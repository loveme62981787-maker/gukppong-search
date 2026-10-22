param()
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$pythonPath = (Get-Command python.exe -ErrorAction Stop).Source
$escapeXml = { param($value) [System.Security.SecurityElement]::Escape($value) }
$kstNow = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(9))
$next = [DateTimeOffset]::new($kstNow.Year, $kstNow.Month, $kstNow.Day, 19, 0, 0, [TimeSpan]::FromHours(9))
if ($next -le $kstNow) { $next = $next.AddDays(1) }
$start = $next.ToString('yyyy-MM-ddTHH:mm:sszzz')
$userId = & $escapeXml ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$exe = & $escapeXml $pythonPath
$arguments = & $escapeXml ('"' + (Join-Path $repo 'batch_daily.py') + '"')
$directory = & $escapeXml $repo
$xml = @"
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>영상 일괄 처리. 처음에는 20개 시험. 등록만 하며 활성화하지 않음.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>$start</StartBoundary><Enabled>true</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>$userId</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>true</StopIfGoingOnBatteries><StartWhenAvailable>false</StartWhenAvailable><Enabled>false</Enabled><Hidden>true</Hidden><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT23H</ExecutionTimeLimit></Settings>
  <Actions Context="Author"><Exec><Command>$exe</Command><Arguments>$arguments</Arguments><WorkingDirectory>$directory</WorkingDirectory></Exec></Actions>
</Task>
"@
# 기존 작업을 덮어쓰지 않는다. -Force 및 작업 활성화/실행 명령을 사용하지 않는다.
Register-ScheduledTask -TaskName 'VideoScoringBatch' -Xml $xml | Select-Object TaskName, State
