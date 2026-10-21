// FM 채점 전용 화면. 잠정 등급 필터와 상태를 공유하지 않는다.
document.addEventListener('DOMContentLoaded', () => {
  const tab = ce('button', 'chip', '✅ 내 채점'); tab.id = 'mmy';
  document.getElementById('ms').after(tab);
  const panel = ce('section', 'sc-wrap'); panel.id = 'my-score-view'; panel.hidden = true;
  document.getElementById('scview').after(panel);
  const style = ce('style');
  style.textContent = '#scgrp{display:none!important} #my-score-view[hidden]{display:none} #my-score-view .grid{padding:0;margin:16px 0} #my-score-view .bar{padding:0;margin:10px 0} #my-score-view .my-thumb{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px} #my-score-view .my-card{padding:12px} #my-score-view .my-card>a{color:var(--ink);text-decoration:none} #my-score-view .my-card h3{font-size:15px;line-height:1.5;margin:10px 0}';
  document.head.append(style);
  scGSel.clear(); scVSel.clear(); MULTIS.forEach(m => m.sync());
  const state = {lists:new Set(listSel), grade:'scored', query:'', sort:'score'};
  let active = false;
  const poolFor = () => V.filter(v => !state.lists.size || [...state.lists].some(k => k === 'hold' ? v._hold : v._lists.includes(k)));
  const matches = (v, grade) => grade === 'unscored' ? !v._sc : grade === 'held' ? v._sc?.held : grade === 'scored' ? v._sc && !v._sc.held : scGradeOK(v, grade);
  const draw = () => {
    panel.replaceChildren();
    panel.append(ce('h2', '', '내 채점 · FM 기준'), ce('p', 'sc-mute', '자막을 읽고 검증한 점수입니다. 영상 탭의 제목·조회수 기반 잠정 등급과 별도로 조회합니다. 숫자는 선택한 목록 기준이며, 검색 전 개수입니다.'));
    const search = ce('input'); search.placeholder = '채점 영상 제목·채널 검색'; search.setAttribute('aria-label', search.placeholder); search.value = state.query;
    const sort = ce('select'); sort.setAttribute('aria-label', '내 채점 정렬');
    for (const [key,label] of [['score','점수 높은 순'],['new','업로드 최신순']]) { const o=ce('option','',label); o.value=key; sort.append(o); }
    sort.value=state.sort;
    const controls=ce('div','bar'); controls.append(search,sort); panel.append(controls);
    const lists=ce('div','bar'); lists.id='my-score-lists';
    for (const [key,label] of LISTS) {
      const count=key==='all'?V.length:V.filter(v=>key==='hold'?v._hold:v._lists.includes(key)).length;
      const name=key==='alert_kr'?'🔔 텔레그램 (한국)':key==='alert_jp'?'🔔 텔레그램 (일본)':label;
      const b=ce('button','chip'+((key==='all'?!state.lists.size:state.lists.has(key))?' on':''),name+' '+count);
      b.onclick=()=>{if(key==='all')state.lists.clear();else if(state.lists.has(key))state.lists.delete(key);else state.lists.add(key);draw();}; lists.append(b);
    }
    panel.append(lists);
    const pool=poolFor(), grades=ce('div','bar'); grades.id='my-score-grades';
    for(const [key,label] of [['scored','채점 완료'],['A','A 이상 (70점~)'],['B','B (55~69)'],['C','C (54 이하)'],['held','채점 보류'],['unscored','미채점']]) {
      const b=ce('button','chip'+(state.grade===key?' on':''),label+' '+pool.filter(v=>matches(v,key)).length);
      b.onclick=()=>{state.grade=key;draw();};grades.append(b);
    }
    panel.append(grades);
    const result=ce('p','sc-mute'), grid=ce('div','grid'); grid.id='my-score-grid'; panel.append(result,grid);
    let visible=48;
    const cards=()=>{
      grid.replaceChildren();
      const q=state.query.trim().toLowerCase();
      const rows=pool.filter(v=>matches(v,state.grade)&&(!q||(v.title+' '+v.channel).toLowerCase().includes(q)));
      rows.sort((a,b)=>{
        const c=v=>v._sc&&!v._sc.held&&scGrade(v._sc)==='C'?1:0;
        return c(a)-c(b)||(state.sort==='new'?String(b.published||'').localeCompare(String(a.published||'')):(b._sc&&!b._sc.held?scTot(b._sc):-1)-(a._sc&&!a._sc.held?scTot(a._sc):-1));
      });
      result.textContent=rows.length+'개 표시 · 선택 목록 '+pool.length+'개';
      if(!rows.length)grid.append(ce('p','empty','조건에 맞는 영상이 없습니다.'));
      for(const v of rows.slice(0,visible)){
        const card=ce('article','card my-card'), link=ce('a');link.href='https://www.youtube.com/watch?v='+encodeURIComponent(v.id);link.target='_blank';link.rel='noopener';
        const img=ce('img','my-thumb');img.src='https://i.ytimg.com/vi/'+encodeURIComponent(v.id)+'/hqdefault.jpg';img.alt=v.title;img.loading='lazy';link.append(img,ce('h3','',v.title));card.append(link,ce('p','sc-mute',(v.channel||'')+' · '+(v.published||'')));
        card.append(v._sc?scTagEl(v._sc):ce('span','tag','미채점'));
        if(v._sc)card.append(scDetailEl(v._sc,false));
        const actions=ce('div','bar'), used=ce('button','chip',(done.has(v.id)?'☑':'☐')+' 사용 완료'), memo=ce('button','chip',memos[v.id]?'📝 메모 있음':'📝 메모');
        used.onclick=()=>{done.has(v.id)?done.delete(v.id):done.add(v.id);saveAll();cards();};
        memo.onclick=()=>{const value=prompt('영상 메모',memos[v.id]||'');if(value!==null){if(value.trim())memos[v.id]=value;else delete memos[v.id];saveAll();cards();}};
        actions.append(used,memo);card.append(actions);grid.append(card);
      }
      if(rows.length>visible){const more=ce('button','chip','더 보기 ('+Math.min(visible,rows.length)+' / '+rows.length+')');more.onclick=()=>{visible+=48;cards();};grid.append(more);}
    };
    search.oninput=()=>{state.query=search.value;visible=48;cards();};sort.onchange=()=>{state.sort=sort.value;visible=48;cards();};cards();
  };
  const previous=setMode;
  setMode=function(m){
    active=m==='my'; previous(active?'s':m); panel.hidden=!active;tab.classList.toggle('on',active);
    if(active){document.getElementById('scview').hidden=true;document.getElementById('ms').classList.remove('on');draw();}
  };
  tab.onclick=()=>setMode('my');
  // 최초 진입 때 숨겨진 FM 필터의 선택이 영상 목록에 남지 않게 한다.
  render();
});
