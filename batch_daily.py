"""하루 한 번 실행하는 일반 프로그램. 중지 상태에서는 외부 호출 없음."""
from contextlib import nullcontext
import hashlib
import json
import os
import subprocess
import sys
import uuid

import batch_score as b

PATHS = ['web/alerts.js', 'data/auto_scores.json', 'web/auto_scores.js']


def command(args, cwd=None):
    result = subprocess.run(args, cwd=cwd or b.s.BASE, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=180,
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'})
    if result.returncode:
        raise RuntimeError('external_command_failed: ' + args[0])
    return result.stdout.strip()


def journal_path():
    return b.s.PRIVATE / 'deployment.json'


def write_journal(journal):
    b.s.atomic(journal_path(), json.dumps(journal, ensure_ascii=False, indent=2))


def file_hashes():
    return {p: hashlib.sha256((b.s.BASE / p).read_bytes()).hexdigest() for p in PATHS}


def check_changes():
    staged = command(['git', 'diff', '--cached', '--name-only']).splitlines()
    changed = command(['git', 'diff', '--name-only']).splitlines()
    if any(p not in PATHS for p in staged + changed):
        raise RuntimeError('unrelated_changes_stop_deployment')


def recover_deployment(locked_state=None):
    """실패한 배포만 복구. 모델을 다시 호출하지 않는다.
    locked_state는 호출자가 score.lock을 이미 쥐고 있을 때만 그 state를 그대로 넘긴다."""
    j = b.s.read_json(journal_path(), None)
    if not j or j['phase'] == 'done':
        return {'deployment': 'nothing_pending'}
    state = locked_state if locked_state is not None else b.s.read_json(b.STATE, b.default_state())
    if not state['enabled'] or state['phase'] != 'production':
        return {'status': 'paused'}
    if j['phase'] == 'preparing':
        # 쓰기 중 전원이 끊겼다면 사용자 변경과 구별할 수 없어 자동 덮어쓰기를 하지 않는다.
        raise RuntimeError('interrupted_preparation_manual_recovery_required')
    check_changes()
    if file_hashes() != j['hashes']:
        raise RuntimeError('files_changed_since_deployment_stop')
    head = command(['git', 'rev-parse', 'HEAD'])
    if j['phase'] == 'ready':
        if head != j['base']:
            raise RuntimeError('head_changed_stop_deployment')
        command([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'])
        command(['node', '--test', 'tests/test_alert_sort.mjs', 'tests/test_scorer.mjs', 'tests/test_list_counts.mjs'])
        if file_hashes() != j['hashes']:
            raise RuntimeError('files_changed_during_tests')
        command(['git', 'add', '--', *PATHS])
        check_changes()
        if not command(['git', 'diff', '--cached', '--name-only']):
            j.update(phase='done')
            write_journal(j)
            return {'deployment': 'no_changes'}
        j.update(phase='committing', tree=command(['git', 'write-tree']))
        write_journal(j)
    if j['phase'] == 'committing':
        head = command(['git', 'rev-parse', 'HEAD'])
        if head == j['base']:
            if command(['git', 'write-tree']) != j['tree']:
                raise RuntimeError('index_changed_stop_deployment')
            command(['git', '-c', 'user.name=loveme62981787-maker', '-c',
                     'user.email=loveme62981787-maker@users.noreply.github.com',
                     'commit', '-m', '절약형 일괄 채점 결과 반영'])
            head = command(['git', 'rev-parse', 'HEAD'])
        if (command(['git', 'rev-parse', 'HEAD^']) != j['base'] or
                command(['git', 'rev-parse', 'HEAD^{tree}']) != j['tree']):
            raise RuntimeError('unexpected_commit_stop_deployment')
        j.update(phase='committed', commit=head)
        write_journal(j)
    if j['phase'] == 'committed':
        if file_hashes() != j['hashes']:
            raise RuntimeError('files_changed_before_push')
        if command(['git', 'rev-parse', 'HEAD']) != j['commit']:
            raise RuntimeError('head_changed_stop_push')
        # 준비 당시 원격과 동일했던 기준 커밋 바로 다음의 이 배포 커밋만 푸시한다.
        command(['git', 'push', 'origin', j['commit'] + ':refs/heads/main'])
        j['phase'] = 'pushed'
        write_journal(j)
    if j['phase'] == 'pushed':
        with (nullcontext() if locked_state is not None else b.locked()):
            state = locked_state if locked_state is not None else b.s.read_json(b.STATE, b.default_state())
            for vid in j['ids']:
                if vid in state['videos']:
                    state['videos'][vid]['status'] = 'published'
            b.save(state)
        j['phase'] = 'done'
        write_journal(j)
    return {'deployment': 'pushed_waiting_for_github_actions'}


def deploy(alert_path, locked_state=None):
    preflight()
    base = command(['git', 'rev-parse', 'HEAD'])
    j = {'phase': 'preparing', 'base': base, 'ids': []}
    write_journal(j)
    # 공개용으로 만들어진 목록만 복사한다. 원본 CSV/자막은 포함하지 않는다.
    b.s.atomic(b.s.BASE / 'web/alerts.js', alert_path.read_text(encoding='utf-8'))
    published = b.publish(locked_state=locked_state)
    j.update(phase='ready', ids=published['ids'], hashes=file_hashes())
    write_journal(j)
    return recover_deployment(locked_state=locked_state)


def preflight():
    if command(['git', 'branch', '--show-current']) != 'main':
        raise RuntimeError('main_branch_required')
    if command(['git', 'status', '--porcelain']):
        raise RuntimeError('working_tree_not_clean')
    command(['git', 'pull', '--ff-only'])
    base = command(['git', 'rev-parse', 'HEAD'])
    if command(['git', 'rev-parse', 'origin/main']) != base:
        raise RuntimeError('unpublished_local_commits_stop_deployment')


def recover_command():
    state = b.s.read_json(b.STATE, b.default_state())
    if not state['enabled']:
        return {'status': 'paused'}
    path = b.s.PRIVATE / 'daily.lock'
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        return recover_deployment()
    finally:
        path.unlink(missing_ok=True)


def daily():
    state = b.s.read_json(b.STATE, b.default_state())
    if not state['enabled']:
        return {'status': 'paused'}
    b.s.PRIVATE.mkdir(parents=True, exist_ok=True)
    lock = b.s.PRIVATE / 'daily.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    previous_input = b.INPUT_ALERTS
    try:
        pending = b.s.read_json(journal_path(), None)
        if pending and pending['phase'] != 'done':
            return recover_deployment()
        if state['phase'] == 'production':
            preflight()
        day = b.now().date().isoformat()
        with b.locked():
            state = b.s.read_json(b.STATE, b.default_state())
            if not state['enabled']:
                return {'status': 'paused'}
            if state.get('last_daily_start') == day:
                return {'status': 'already_started_today'}
            state['last_daily_start'] = day
            b.save(state)
        private = b.s.BASE.parent / 'koreatambang-alert-private'
        command(['git', 'pull', '--ff-only'], private)
        # 시험도 공개 저장소에 변경을 남기지 않는다.
        alert_path = b.s.PRIVATE / ('batch-alerts-' + uuid.uuid4().hex + '.js')
        command([sys.executable, str(b.s.BASE / 'alerts_to_js.py'), '--dir', str(private / 'alerts'), '--out', str(alert_path)])
        if not alert_path.exists():
            return {'status': 'no_alert_csv_keep_existing_data'}
        b.INPUT_ALERTS = alert_path
        # 통과한 영상마다 즉시 게시한다. 시험 단계는 콜백을 연결하지 않는다.
        on_staged = (lambda locked_state: deploy(alert_path, locked_state=locked_state)) if state['phase'] == 'production' else None
        summary = b.run_batch(on_staged=on_staged)
        return summary
    finally:
        b.INPUT_ALERTS = previous_input
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        result = recover_command() if sys.argv[1:] == ['recover'] else daily()
        print(json.dumps(result, ensure_ascii=True))
    except Exception as error:
        print(json.dumps({'status': 'stopped', 'reason': type(error).__name__}))
        sys.exit(1)
