# -*- coding: utf-8 -*-
"""'글로벌 콘텐츠' 12개 갈래·140꼭지 — 외국인이 한국에서 겪고 말하는 영상을 찾아 web/global_topics.js 로 저장

    python global_topics_watch.py            검색 → web/global_topics.js
    python global_topics_watch.py --dry      저장 없이 요약만 출력
    python global_topics_watch.py --check    규칙(정규식) 검증만

GROUPS 가 갈래·꼭지·판별 규칙·검색어의 기준이다. 사이트(web/index.html)도 global_topics.js 안의 GLOBAL_TOPICS 를 그대로
읽어 기존 영상까지 같은 규칙으로 분류하므로, 꼭지를 고치려면 여기만 고치면 된다.
규칙은 제목에만 적용하고(대소문자 무시), JS·파이썬 공통 정규식 문법만 쓴다. (한글 옆에는 \\b 를 쓰지 않는다)
experience_watch.py 의 검색·파싱 함수를 재사용한다. (API 키 불필요, 표준 라이브러리만 사용)
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import experience_watch as ew

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "global_topics.js")
STORE = os.path.join(BASE, "global_topics_store.json")
KST = timezone(timedelta(hours=9))
MIN_SEC = 181
MAX_ITEMS = 1500

# (갈래 이름, 갈래 설명, [(꼭지 이름, 판별 규칙, 영어 검색어), ...])
GROUPS = [
    ("🚨 안전·치안", "혼자 있어도 괜찮다는 장면 — 말보다 화면이 증거", [
        ("새벽에 혼자 걸어도 되는 거리", r"walk(ing)? alone|alone at night|safe at night|late night walk|safest|새벽에 혼자|혼자 걷", "foreigner walking alone at night Korea safe"),
        ("카페에 노트북·가방 두고 자리 비우기", r"(leave|left|leaving).{0,20}(laptop|bag|phone).{0,30}(cafe|table)|노트북.{0,10}(두고|자리)|가방 두고", "leaving laptop bag at cafe Korea foreigners shocked"),
        ("카페 자리 맡아두고 잠깐 다녀오기", r"saving (a )?seat|reserve.{0,10}seat|자리 맡|자리를 맡", "Korea cafe save seat leave belongings foreigners"),
        ("지하철 유실물이 돌아오는 과정", r"lost (and found|phone|wallet|item)|유실물|분실|lost property|returned my", "lost phone subway Korea returned foreigner"),
        ("무인 매장·무인 아이스크림 가게", r"unmanned|no staff|무인 (매장|아이스크림|가게)|ice cream store.{0,15}(no|without)", "unmanned ice cream store Korea foreigners"),
        ("편의점 안심부스·안심귀갓길", r"safe (return|route|booth|zone|walk)|안심(부스|귀갓길|귀가)|women'?s? safety", "Korea safe return home route safety booth foreigners"),
        ("아이 혼자 학원 다녀오는 풍경", r"kids? (alone|by themselves)|children.{0,15}alone|학원.{0,10}(혼자|아이)|walking home alone", "Korean kids walking alone hagwon foreigners"),
        ("지하철에서 폰 든 채로 졸기", r"sleep(ing)? (on|in) (the )?(subway|metro)|asleep.{0,15}(subway|metro)|지하철.{0,8}(졸|자는)|dozing", "sleeping on subway holding phone Korea foreigner"),
        ("택배 문 앞에 하루 놔둬도 되는 것", r"packages?.{0,20}(door|outside|hallway)|parcels?.{0,20}(door|outside)|택배.{0,10}(문 앞|현관)|doorstep", "Korea packages left at door safe foreigners"),
        ("길거리 CCTV 밀도", r"cctv|surveillance|감시카메라|씨씨티비", "CCTV everywhere Korea foreigners"),
        ("여성 1인 가구 원룸 생활", r"solo female|woman.{0,15}(living )?alone|girl.{0,15}living alone|\bone.?room\b|원룸|1인 가구|living alone", "foreign woman living alone Korea one room safe"),
        ("술자리 끝난 새벽 거리", r"after (a night of )?drinking|drunk.{0,15}(street|night)|술자리 (끝|후)|새벽 거리|late night.{0,10}street", "Korea streets after drinking night safe foreigners"),
    ]),
    ("🚇 대중교통·이동", "'정확함'이 콘텐츠가 된다 — 시계와 같이 찍기", [
        ("지하철·버스 배차 간격과 정시성", r"punctual|on time|waiting time|배차|정시|every (2|3|5) minutes|arrival time", "Korea subway bus punctual frequency foreigners reaction"),
        ("정류장 도착 정보 전광판", r"arrival (info|board|screen)|bus (stop )?(board|app|info)|전광판|도착 정보|real.?time (bus|arrival)", "Korea bus stop arrival board foreigners"),
        ("교통카드 한 장으로 버스·지하철·택시", r"t-?money|transit card|교통카드|티머니|climate card|k-?pass|one card", "T-money card Korea foreigners how to use"),
        ("환승 할인 계산해 보기", r"transfer (discount|fee)|free transfer|환승|cheap (transit|transport)|transport fare", "Korea transfer discount subway bus fare foreigners"),
        ("지하철역 내부 상점·편의시설", r"(inside|in) (the )?(subway )?station.{0,20}(shop|store|mall)|역사 (내|안)|station shops?", "inside Korean subway station shops facilities foreigners"),
        ("지하상가 문화", r"underground (shopping|mall|market|street)|지하상가|gotomall|goto mall", "Korea underground shopping mall foreigners"),
        ("역 화장실 청결도", r"clean (public )?(toilet|restroom|bathroom)|public (toilet|restroom|bathroom)|공중화장실|화장실.{0,6}(깨끗|청결)", "Korea public toilets clean subway foreigners"),
        ("KTX 속도·좌석 체험", r"ktx|srt|bullet train|high.?speed (rail|train)|고속열차|고속철", "KTX first time foreigner Korea train"),
        ("심야버스(N버스)", r"night bus|\bn bus\b|심야버스|n버스|owl bus|late.?night bus", "Korea night bus N bus foreigners"),
        ("택시 앱 호출·자동 결제", r"kakao ?t\b|taxi app|택시 앱|uber.{0,15}korea|auto.?pay.{0,10}taxi|카카오t", "Kakao T taxi Korea foreigners"),
        ("공항철도·입국 수속 속도", r"airport (railroad|railway|express)|arex|공항철도|immigration|입국 (수속|심사)|incheon airport", "Incheon airport arrival immigration speed foreigners Korea"),
        ("따릉이 공유 자전거", r"ttareungi|따릉이|bike ?share|shared bike|rental bike|public bike", "Seoul Ttareungi bike share foreigners"),
        ("노약자석·임산부석 문화", r"priority seat|pink seat|elderly seat|노약자|임산부석|pregnant seat|seat for (the )?elderly", "Korea subway priority seat culture foreigners"),
        ("터널에서도 끊기지 않는 데이터", r"(signal|wi.?fi|internet|data|5g).{0,25}(subway|tunnel|underground)|(subway|tunnel|underground).{0,25}(signal|wi.?fi|internet|5g)|터널.{0,8}(데이터|와이파이)", "Korea subway internet signal underground tunnel foreigners"),
    ]),
    ("⚡ 편의·속도", "'빨리빨리'는 주제가 아니라 소재 창고다", [
        ("앱 하나로 다 되는 배달", r"delivery app|baemin|배달의민족|배민|coupang eats|yogiyo|요기요|배달 앱|food delivery.{0,15}korea", "Korea delivery app baemin foreigners"),
        ("새벽 배송·당일 배송", r"dawn delivery|same.?day delivery|rocket delivery|새벽 ?배송|당일 ?배송|overnight delivery|next.?day delivery|coupang", "Korea dawn delivery Coupang foreigners shocked"),
        ("편의점 밀도와 퀄리티", r"convenience stores?|\bcu\b|gs25|7-?eleven|편의점|emart24|cvs", "Korean convenience store foreigners reaction"),
        ("24시간 카페·식당·편의점", r"24.?hours?|24시간|open all night|always open|open 24|late.?night (food|open)", "Korea 24 hour places cafe restaurant foreigners"),
        ("택배 속도 실측", r"parcel.{0,15}(speed|fast)|package.{0,15}(speed|fast|arrive)|택배.{0,6}(속도|빠)|delivery speed|ships? (overnight|next day)", "Korea parcel delivery speed test foreigners"),
        ("민원·행정 처리 속도", r"government office|ward office|visa.{0,15}(fast|quick|easy)|민원|행정 처리|alien registration|resident registration|\barc\b|immigration office", "Korea government office fast foreigner experience ARC"),
        ("카드·간편결제 보급률", r"contactless|cashless|samsung pay|kakao ?pay|naver ?pay|간편결제|apple pay|tap (to )?pay|card only|no cash|카드 결제", "Korea cashless payment foreigners no cash"),
        ("무료 와이파이", r"free wi.?fi|무료 와이파이|public wi.?fi|wifi everywhere", "Korea free wifi everywhere foreigners"),
        ("인터넷 속도 측정", r"internet speed|speed ?test|인터넷 속도|fast internet|gigabit|fiber|5g speed|와이파이 속도", "Korea internet speed test foreigners"),
        ("키오스크·1인 주문기", r"kiosks?|키오스크|self.?order|ordering machine|order.{0,10}screen", "Korea kiosk ordering foreigners"),
        ("병원 당일 진료와 진료비", r"hospital.{0,20}(cost|price|fast|same day|visit|experience)|clinic.{0,15}(cost|price|visit)|진료비|병원 (당일|진료)|medical cost|healthcare.{0,15}korea|doctor.{0,15}korea", "Korea hospital same day treatment cost foreigners"),
        ("약국 접근성", r"pharmac(y|ies)|약국|over.?the.?counter|drugstore.{0,10}korea|medicine.{0,15}korea", "Korean pharmacy foreigners experience"),
        ("세탁·수선 당일 처리", r"laundry|laundromat|dry.?clean|수선|세탁|alteration|coin laundry|빨래방", "Korea laundry same day alteration foreigners"),
        ("은행 앱 즉시 이체", r"banking app|bank transfer|\btoss\b|kakao ?bank|은행 앱|즉시 이체|instant transfer|open (a )?bank account|bank account.{0,15}korea", "Korea banking app instant transfer Toss foreigners"),
        ("무인 사진관·무인 스터디카페", r"photo ?booth|unmanned (photo|studio)|무인 (사진|스터디)|study cafe|스터디카페|self.?photo|life ?4 ?cuts|four ?cuts|photoism", "Korea unmanned photo studio study cafe foreigners"),
        ("로봇 서빙·무인 계산", r"robot (waiter|server|serving|barista|cafe|restaurant)|서빙 로봇|로봇 (서빙|카페)|self.?checkout|무인 계산", "Korea robot serving restaurant foreigners"),
        ("중고거래 앱으로 동네 거래", r"danggeun|daangn|carrot market|중고거래|당근|second.?hand (app|market)|used goods|bunjang|번개장터", "Korea Danggeun used goods app foreigners"),
        ("분실물 찾아주기", r"lost (and found|wallet|phone|item)|분실물|lost property|found my (wallet|phone)|returned (my|the) (wallet|phone)", "lost wallet Korea returned foreigner"),
    ]),
    ("🍚 음식·식문화", "먹는 장면은 언어가 필요 없다 — 소리를 크게", [
        ("혼밥이 가능한 분위기", r"eat(ing)? alone|solo (dining|eating|meal)|honbap|혼밥|dining alone|table for one|eating by myself", "eating alone in Korea honbap foreigners"),
        ("1인 메뉴가 잘 갖춰진 식문화", r"solo (menu|portion)|single (portion|serving)|1인 ?(메뉴|분|세트)|one.?person (menu|portion|set)", "Korea solo dining menu single portion foreigners"),
        ("반찬이 기본으로 깔리는 상", r"side dishes|banchan|panchan|반찬|free (side|refill)|complimentary side", "Korean banchan side dishes foreigners reaction"),
        ("고기 구워 먹는 테이블", r"korean bbq|kbbq|k-bbq|samgyeopsal|삼겹살|grill(ing)? (at|on) the table|고기 ?구|galbi|갈비|korean barbecue", "Korean BBQ first time foreigners"),
        ("치킨 + 맥주 조합", r"chimaek|치맥|fried chicken|치킨|chicken (and|&|with) beer|korean fried chicken", "Korean fried chicken and beer chimaek foreigners"),
        ("국밥·해장 문화", r"gukbap|hangover (soup|food|cure)|해장|국밥|haejang|pork soup|ox bone soup|hangover.{0,15}korea", "Korean hangover soup haejang gukbap foreigners"),
        ("분식 (떡볶이·김밥·순대)", r"tteokbokki|topokki|떡볶이|gimbap|kimbap|김밥|sundae|순대|bunsik|분식|korean street food|street food.{0,15}korea", "Korean street food tteokbokki gimbap foreigners"),
        ("편의점 음식만으로 하루", r"convenience store (food|meal|only)|편의점 (음식|밥|도시락)|(only|just).{0,15}convenience store|day.{0,15}convenience store|cvs food", "eating only convenience store food in Korea one day foreigners"),
        ("한국식 중식 (짜장면·탕수육)", r"jajangmyeon|짜장면|tangsuyuk|탕수육|korean.?chinese|jjamppong|짬뽕|black bean noodles", "Korean Chinese food jajangmyeon foreigners"),
        ("족발·보쌈·찜닭", r"jokbal|족발|bossam|보쌈|jjimdak|찜닭|pig trotters|pork feet|braised (chicken|pork)", "jokbal bossam Korean food foreigners try"),
        ("시장 먹거리 순례", r"market food|food (tour|market)|시장 (먹|음식|투어)|gwangjang|namdaemun market|night market|야시장|korean market", "Korean market food tour Gwangjang foreigners"),
        ("매운맛 단계 도전", r"spic(y|iest)|매운|buldak|불닭|hot chicken|spice (level|challenge)|fire noodle|맵기|맵다", "Korean spicy food challenge foreigners"),
        ("물·반찬·수저 셀프", r"self.?service (water|side|restaurant)|셀프|get your own|self (serve|refill)|spoons? (in|from) (a |the )?drawer|water.{0,10}self", "Korea self service water side dishes restaurant foreigners"),
        ("식후 커피가 코스인 문화", r"coffee after (a )?(meal|lunch|dinner)|after.?meal coffee|식후 커피|post.?meal coffee|cafe after (eating|lunch)|iced americano", "Korea coffee after lunch culture foreigners"),
        ("회식 1차·2차", r"hoesik|회식|company dinner|work dinner|after.?work (dinner|drinks?)|1차|2차|round (1|2|two)|office dinner|team dinner", "Korean company dinner hoesik foreigners"),
        ("프랜차이즈 경쟁력", r"franchise|프랜차이즈|chain (store|restaurant|cafe)s?|mega ?coffee|compose coffee|paik'?s|lotteria|bbq chicken|bhc", "Korean franchise restaurants chains foreigners compare"),
        ("배달 포장 단위와 그릇 반납", r"dish(es)? (return|pickup|outside)|그릇 (반납|내놓)|reusable (dish|container|plate)|배달 포장|delivery packaging|multi.?use (dish|container)|다회용기", "Korea delivery packaging reusable dishes foreigners"),
        ("한강 라면 · 치킨 배달", r"han river.{0,25}(ramen|ramyeon|chicken|delivery|picnic)|한강 (라면|치킨|배달)|ramyeon (machine|cooking)|ramen (machine|cooking).{0,10}(han|river|park)|delivery.{0,15}(park|river)", "Han River ramen chicken delivery picnic foreigners"),
    ]),
    ("☕ 카페·디저트", "인테리어 한 컷이 썸네일이 된다", [
        ("카페 인테리어 퀄리티", r"cafe (interior|design|aesthetic)|카페 인테리어|aesthetic cafe|beautiful cafe|hip cafe|인테리어", "Korean cafe interior design foreigners"),
        ("디저트 카페 다양성", r"dessert cafe|디저트|bingsu|빙수|croissant|korean (bakery|desserts?)|dessert.{0,10}korea", "Korean dessert cafe bingsu foreigners"),
        ("교외 대형 베이커리 카페", r"bakery cafe|giant (cafe|bakery)|huge (cafe|bakery)|대형 베이커리|베이커리 카페|large bakery|countryside cafe|suburb.{0,10}cafe", "huge bakery cafe outside Seoul Korea foreigners"),
        ("카공족 풍경", r"study(ing)? (at|in) (a |the )?cafes?|cagong|카공|students.{0,15}cafes?|working.{0,10}cafes?.{0,10}korea", "Korea students studying in cafes cagong foreigners"),
        ("테마 카페 (동물·전시·굿즈)", r"theme(d)? cafe|animal cafe|cat cafe|dog cafe|sheep cafe|raccoon cafe|테마 ?카페|굿즈 카페|character cafe|pop.?up cafe", "Korean themed cafe animal cafe foreigners"),
        ("밤늦게까지 하는 카페", r"late.?night cafe|cafe.{0,15}(open|until) (late|24|3 ?am|2 ?am)|24.?hour cafe|심야 카페|밤늦게까지.{0,6}카페|cafe.{0,15}all night", "Korea late night cafe open late foreigners"),
        ("커피 가격대 비교", r"coffee (price|cost)s?|(price|cost) of coffee|americano.{0,15}(price|won|cheap)|cheap coffee|커피 가격|1,?500 won coffee", "Korean coffee prices compare foreigners"),
        ("길거리 포장마차 감성", r"pojangmacha|포장마차|tent bar|orange tent|street (tent|stall)s?|pocha", "Korean pojangmacha street tent bar foreigners"),
    ]),
    ("🌙 밤·놀거리", "밤이 살아있다 — 해외 도시와 가장 갈리는 지점", [
        ("노래방", r"noraebang|노래방|karaoke", "Korean karaoke noraebang foreigners"),
        ("코인노래방", r"coin (karaoke|noraebang|singing)|코인 ?노래방|coin.{0,10}sing", "Korea coin karaoke foreigners"),
        ("PC방 (+ PC방 음식)", r"pc ?bang|pc방|피시방|internet cafe|gaming cafe|pc cafe", "Korean PC bang foreigners experience"),
        ("찜질방", r"jjimjilbang|jimjilbang|찜질방|korean spa|korean sauna|bathhouse|public bath|spa.{0,10}korea|sauna.{0,10}korea", "Korean jjimjilbang first time foreigners"),
        ("포토부스·인생네컷", r"photo ?booth|life ?(4|four) ?cuts|인생 ?네컷|four ?cuts|photoism|photo (sticker|studio)", "Life4Cuts photo booth Korea foreigners"),
        ("방탈출·보드게임 카페", r"escape room|방탈출|board ?game cafe|보드게임|puzzle room", "Korea escape room board game cafe foreigners"),
        ("밤늦게까지 하는 쇼핑", r"late.?night shopping|night shopping|심야 쇼핑|밤 쇼핑|shopping at night|shopping.{0,12}(2|3|4) ?am", "Korea late night shopping foreigners"),
        ("동대문 야간 쇼핑", r"dongdaemun|동대문|\bddp\b|doota|\bapm\b|wholesale market|도매", "Dongdaemun night shopping foreigners"),
        ("늦은 밤까지 살아있는 상권", r"busy at night|nightlife|streets? (are )?alive|never sleeps|야간 상권|밤새|밤거리|밤 거리|(2|3|4) ?am.{0,15}(street|seoul|korea)|late at night.{0,15}(street|seoul|korea)", "Korea streets alive at 3am nightlife foreigners"),
        ("밤에도 불 켜진 거리", r"lit up at night|neon (lights|signs)|night (view|walk)|밤에도|city lights|lights at night|seoul at night|korea at night|야경", "Seoul night walk neon lights foreigners"),
        ("야구장 응원 문화", r"baseball|야구|\bkbo\b|ballpark|cheer(ing)? (song|squad|culture)|응원 문화|lotte giants|lg twins|doosan bears|kia tigers", "Korean baseball game cheering culture foreigners first time"),
        ("한강 야경·남산·롯데타워", r"han river.{0,15}(night|view)|한강 야경|namsan|남산|n seoul tower|lotte (world )?tower|롯데타워|seoul tower|banpo.{0,15}(bridge|fountain)|반포", "Han River night view Namsan Lotte Tower foreigners"),
    ]),
    ("💄 뷰티·쇼핑", "체험형이라 조회수가 붙는다 — 전후 비교 필수", [
        ("K뷰티 로드숍 밀집", r"k-?beauty|korean (skincare|beauty|cosmetics)|innisfree|로드숍|스킨케어|skincare shopping|beauty shopping|myeongdong.{0,20}(beauty|shop|skincare)", "K-beauty shopping Myeongdong foreigners"),
        ("화장품 샘플·테스트 문화", r"samples?\b|testers?\b|무료 샘플|화장품 샘플|free samples?|cosmetics? (sample|test)|try before", "Korean cosmetics samples testers foreigners"),
        ("올리브영 같은 드럭스토어", r"olive ?young|올리브영|health and beauty store|olive young haul|drug ?store.{0,10}korea", "Olive Young haul foreigners first time"),
        ("성형·피부과 접근성", r"plastic surgery|cosmetic surgery|dermatolog|skin (clinic|treatment)|성형|피부과|aesthetic clinic|botox|laser (treatment|clinic)|derma clinic", "foreigner dermatology skin clinic Korea cost"),
        ("미용실 가격과 속도", r"hair ?salon|haircut|hairdresser|\bperm\b|미용실|barber|hair (dye|color|colour)|salon.{0,10}(price|korea)", "foreigner hair salon Korea price haircut"),
        ("안경점 당일 제작", r"glasses.{0,20}(korea|same.?day|cheap|made)|eyeglasses|optician|안경|same.?day (glasses|lenses)|optical shop", "foreigner glasses Korea same day made cheap"),
        ("남성 그루밍·화장품", r"men'?s (grooming|skincare|makeup|cosmetics)|male (beauty|makeup|skincare)|남성 (화장품|그루밍|메이크업)|korean men.{0,15}(makeup|skincare|grooming)", "Korean men grooming makeup skincare foreigners"),
        ("온라인 쇼핑 반품 속도", r"return (policy|speed|process)|refund|반품|online shopping.{0,15}(return|korea)|coupang return|free returns?|easy return", "Korea online shopping return refund speed foreigners"),
    ]),
    ("🏞 도시·자연·풍경", "계절을 찍어두면 1년 내내 다시 쓴다", [
        ("산이 가까워 당일 등산", r"hik(e|ing)|등산|bukhansan|북한산|trekking|inwangsan|산행|bugaksan|mountain.{0,15}(seoul|korea)", "hiking in Seoul mountain day trip foreigners"),
        ("좁은 땅에 산·강·바다·도시", r"small country|compact (country|city)|산.{0,3}강.{0,3}바다|everything (is )?(close|nearby)|so close together|mountains?.{0,12}(sea|ocean|river).{0,12}(city|seoul)", "Korea small country mountains sea city all close foreigners"),
        ("한강공원", r"han ?river park|hangang park|한강 ?공원|han river (picnic|walk|park)|yeouido park|banpo park", "Han River park picnic foreigners"),
        ("도심 속 산책로·공원 접근성", r"city (park|trail|walk)|산책로|urban (park|trail)|walking trail|park in (the )?city|seoullo|seoul forest|서울숲|서울로", "Seoul urban park walking trail foreigners"),
        ("청계천", r"cheonggyecheon|청계천|cheonggye stream", "Cheonggyecheon stream walk Seoul foreigners"),
        ("초대형 도시인데 산책 코스가 많은 점", r"walking (courses?|routes?)|산책 코스|many parks|seoul walk(ing)?|walking tour|둘레길|dulle-?gil", "Seoul walking courses big city green foreigners"),
        ("사계절이 뚜렷한 풍경", r"four seasons(?! ?(hotel|seoul|spa|resort))|사계절|season (change|changes)|each season|all four seasons", "Korea four seasons beautiful foreigners"),
        ("벚꽃 시즌 도시 분위기", r"cherry blossoms?|벚꽃|jinhae|yeouido.{0,15}(spring|blossom)|blossom season|sakura.{0,10}korea", "Korea cherry blossom season foreigners"),
        ("가을 단풍과 은행나무", r"autumn (leaves|foliage|colors?)|fall (foliage|colors?|leaves)|단풍|ginkgo|은행나무|naejangsan|maple leaves", "Korea autumn foliage ginkgo foreigners"),
        ("궁궐 옆 고층빌딩의 대비", r"palace.{0,25}(skyscraper|high.?rise|modern|skyline)|궁궐.{0,10}(고층|빌딩)|gyeongbokgung.{0,20}(contrast|modern)|old and new|전통과 현대", "Seoul palace skyscraper contrast tradition modern foreigners"),
        ("전통과 초현대가 붙어 있는 풍경", r"traditional (and|meets) (modern|futuristic)|tradition meets|old meets new|전통과 초현대|hanok.{0,20}(skyscraper|modern)|ikseon|bukchon.{0,20}(modern|skyscraper)", "Korea traditional meets futuristic modern foreigners"),
        ("눈 오는 날 도시", r"snow(y|ing|fall)?\b|first snow|눈 오는|눈 내리는|winter (in )?(seoul|korea)|snow day", "Seoul snow day winter foreigners"),
        ("장마와 한여름 폭염", r"monsoon|rainy season|장마|heat ?wave|폭염|humid|summer (heat|in korea)|jangma|hot summer|무더위", "Korea monsoon heatwave summer foreigners"),
        ("부산·제주·섬", r"busan|부산|jeju|제주|ulleungdo|울릉도|geoje|거제|namhae|남해|udo|gadeokdo", "Busan Jeju island trip foreigners"),
    ]),
    ("🏯 전통·문화유산", "'옛것'이 아니라 '지금 쓰는 옛것'으로 찍는다", [
        ("한복 체험과 궁궐 산책", r"hanbok|한복|palace (walk|visit|stroll|tour)|gyeongbokgung|경복궁|changdeokgung|덕수궁|royal palace", "hanbok rental palace walk foreigners Seoul"),
        ("궁궐 야간 개장", r"palace (at )?night|night opening|야간 ?개장|(night|moonlight) (tour|viewing).{0,15}palace|달빛 기행|gyeongbokgung night", "Korean palace night opening foreigners"),
        ("한글 간판이 주는 통일감", r"hangul|한글|korean (alphabet|signs?|writing|script)|signs? in korean|learn(ed|ing)? korean (alphabet|letters)", "Hangul signs Korean alphabet foreigners learn"),
        ("한옥마을·한옥 카페", r"hanok (village|cafe|stay|guesthouse)|한옥|bukchon|jeonju hanok|ikseon|traditional (korean )?house", "hanok village stay cafe foreigners"),
        ("전통시장 하루", r"traditional market|전통시장|market day|gwangjang market|mangwon market|namdaemun market|dongdaemun market", "Korean traditional market day foreigners"),
        ("절·템플스테이", r"temple ?stay|템플스테이|buddhist temple|korean temple|monk|jogyesa|bulguksa|haeinsa|temple food|사찰", "Korea temple stay experience foreigners"),
        ("명절 풍경", r"chuseok|추석|seollal|설날|lunar new year|명절|korean holiday|korean thanksgiving|family gathering", "Chuseok Seollal Korean holiday foreigners experience"),
        ("국립박물관·무료 전시", r"national museum|국립중앙박물관|free (museum|exhibit|exhibition)|무료 전시|museum.{0,15}(free|korea)|museum of korea", "National Museum of Korea free exhibit foreigners"),
    ]),
    ("🎓 사회 시스템·교육", "설명이 필요한 주제 — 반응 인터뷰와 궁합이 좋다", [
        ("교육열이 도시 분위기까지 만드는 점", r"education (fever|system|culture)|교육열|study hard|academic pressure|school culture|korean students|competition.{0,15}school", "Korean education system study culture foreigners reaction"),
        ("수능 날 도시 전체가 반응하는 문화", r"suneung|수능|csat|college entrance exam|exam day|test day", "Suneung exam day Korea whole country foreigners"),
        ("학원가 풍경", r"hagwon|학원|cram school|academy district|daechi|대치|private academy|tutoring", "Korean hagwon cram school district foreigners"),
        ("DMZ처럼 분단 현실을 체감하는 특수성", r"\bdmz\b|demilitarized|panmunjom|판문점|분단|\bjsa\b|imjingak|임진각|dora observatory|north korea border", "DMZ tour foreigners Korea division"),
        ("군 복무", r"military service|군 복무|korean army|conscription|군대|enlist|national service|bts.{0,15}military", "Korean military service conscription foreigners react"),
        ("아파트 단지 중심의 생활 편의성", r"apartment (complex|life|living|tour)|아파트|korean apartment|apt complex|high.?rise (living|apartment)", "Korean apartment complex living convenience foreigners"),
        ("동네마다 병원·약국·편의점이 몰린 구조", r"everything (in|within) walking|walkable|within walking distance|병원.{0,6}약국.{0,6}편의점|clinic.{0,10}pharmacy.{0,10}convenience", "Korea neighborhood hospital pharmacy convenience store everywhere foreigners"),
        ("의료보험·병원비", r"health ?insurance|의료보험|\bnhis\b|national health|건강보험|medical (bill|insurance|cost)|hospital (bill|cost)|병원비|cheap (healthcare|doctor)", "Korea national health insurance hospital bill foreigners"),
        ("분리수거·쓰레기 종량제", r"recycling|분리수거|trash (bag|rules?|system)|garbage|쓰레기|종량제|waste (sorting|separation)|food waste|음식물", "Korea recycling trash bag rules foreigners"),
        ("본인인증·모바일 신분증", r"digital id|mobile id|본인인증|identity verification|모바일 신분증|real.?name (verification|system)|resident registration number", "Korea mobile ID identity verification foreigners"),
        ("전세라는 제도", r"jeonse|전세|key money|deposit.{0,10}rent|\bwolse\b|월세|rental system|housing deposit", "Korea jeonse rental system foreigners explained"),
        ("지하철·공공시설 무료 화장실", r"free (public )?(toilets?|restrooms?|bathrooms?)|무료 화장실|clean toilets|toilet paper|공중화장실", "Korea free public toilets clean foreigners"),
    ]),
    ("🙇 사람·예의·정서", "오해 사기 쉬운 갈래 — 반드시 '차이'로 말할 것", [
        ("거리에서 들리는 한국식 예의 표현", r"korean etiquette|korean manners|polite (greeting|phrases?|expressions?)|bow(ing)? (to|down)|예의|존댓말|honorifics?|politeness", "Korean etiquette manners politeness foreigners"),
        ("\"눈치\"가 생활 시스템으로 작동하는 점", r"nunchi|눈치|reading the room|read the (air|room)|social awareness", "nunchi Korean culture foreigners explained"),
        ("줄 서기 질서", r"queue|queuing|line(s)? up|줄 ?서|waiting in line|orderly|standing in line|줄서기", "Korea queue order waiting in line foreigners"),
        ("나이·호칭 문화 (형·누나·선배)", r"age (culture|hierarchy)|hyung|noona|sunbae|oppa|unnie|호칭|형|누나|선배|korean age", "Korean age culture hyung noona sunbae foreigners"),
        ("덤·서비스로 나오는 정", r"jeong|free (extra|service)|덤|서비스로|extra food|bonus (food|side)|generous|ajumma|아줌마|이모", "Korean jeong generosity free service extra foreigners"),
        ("처음 만나 나이부터 묻는 문화", r"asks? (my |your )?age|ask(ed|ing)? (me )?how old|how old are you|나이부터|나이 ?묻|age question|age.{0,10}first meeting", "Koreans ask your age first meeting foreigners"),
        ("커플 기념일·커플룩", r"couple (outfit|look|clothes|culture|anniversary|items?|ring)|커플룩|커플 기념일|100 days|matching outfit|anniversar", "Korean couple culture matching outfits anniversaries foreigners"),
        ("단체 사진 포즈", r"group photo|단체 ?사진|v sign|peace sign|photo pose|사진 포즈|selfie culture|photo spot", "Korean group photo pose V sign foreigners"),
        ("배려석·자리 양보", r"give up (a |your |my )?seat|seat (for|offered)|자리 ?양보|배려석|offering (a )?seat|courtesy seat|priority seat", "Korea giving up seat subway culture foreigners"),
    ]),
    ("🎤 K팝·팬덤·콘텐츠", "이미 검색량이 있는 갈래 — 진입은 쉽고 경쟁도 세다", [
        ("아이돌·팬덤·응원봉", r"idol|fandom|fan ?(club|culture)|light ?stick|응원봉|아이돌|팬덤|army bomb|blackpink|stray kids|newjeans|aespa|\btwice\b|seventeen|\bbts\b", "K-pop idol fandom lightstick foreigners experience"),
        ("팬사인회·생일카페", r"fan ?sign|사인회|birthday cafe|생일 ?카페|fan event|fan meeting|팬미팅|cup ?sleeve|photocard|포토카드", "K-pop fansign birthday cafe foreigners"),
        ("음악방송 공개방송", r"music (show|bank|core)|공개방송|inkigayo|m ?countdown|show champion|뮤직뱅크|음악방송|인기가요|show! music core", "K-pop music show recording audience foreigners attend"),
        ("연습생 시스템", r"trainee|연습생|idol training|audition|k-?pop training|casting|training system", "K-pop trainee system audition foreigners"),
        ("K드라마 촬영지 성지순례", r"filming location|촬영지|k-?drama (location|filming|set)|pilgrimage|성지순례|drama (set|spot|tour)|crash landing|goblin|itaewon class", "K-drama filming locations tour foreigners"),
        ("노래방에서 K팝 부르기", r"sing(ing)? (k-?pop|bts|blackpink|newjeans)|k-?pop (karaoke|noraebang)|노래방.{0,15}(케이팝|k팝|k-pop)|karaoke.{0,15}k-?pop", "singing K-pop at Korean karaoke noraebang foreigners"),
        ("지하철 아이돌 생일 광고", r"birthday (ad|ads|advertisement)|subway (ad|ads|advertis)|idol (ad|ads)|지하철 광고|생일 광고|fan (ad|ads)|cheering ad|bus ad", "K-pop idol birthday subway ads foreigners"),
    ]),
]
JP = "--jp" in sys.argv   # 일본 버전: 같은 12갈래·140꼭지를 일본 상황으로 옮긴 global_topics_jp_groups.py 를 쓴다
if JP:
    from global_topics_jp_groups import GROUPS_JP
    GROUPS = GROUPS_JP
    OUT = os.path.join(BASE, "web", "global_topics_jp.js")
    STORE = os.path.join(BASE, "global_topics_jp_store.json")
COUNTRY = "일본" if JP else "한국"
EXPECT = [12, 14, 18, 18, 8, 12, 8, 14, 8, 12, 9, 7]
SORTS = ["EgIQAQ%3D%3D", "CAISBAgEEAE%3D"]   # 관련도순 / 이번 달 최신순 (꼭지 영어 검색은 앞의 것만, 갈래 검색은 둘 다)
KR_WORDS = ["korea", "korean", "seoul", "busan", "jeju", "incheon", "k-pop", "kpop", "k-drama", "kdrama", "k-beauty", "han river", "한국", "서울", "부산", "제주", "한류", "한강", "한복", "韓国"]
# 외국인 시선(사용·경험·반응)이 제목에 드러나는지. '해외' 한 단어만으로는 통과시키지 않는다 (경제 뉴스 등이 섞임)
JP_WORDS = ["japan", "japanese", "tokyo", "osaka", "kyoto", "hokkaido", "okinawa", "fukuoka", "nara", "hiroshima", "nagoya", "j-pop", "jpop", "anime", "manga", "shinkansen", "일본", "도쿄", "오사카", "교토", "후쿠오카", "삿포로", "오키나와", "日本", "東京", "大阪", "京都"]
WORDS = JP_WORDS if JP else KR_WORDS
FOREIGN_VIEW = re.compile(r"foreigners?|tourists?|expats?|first time|react|reaction|\btry\b|\btried\b|trying|experience|living in|moved to|vlog|외국인|외국 ?사람|해외 ?(반응|네티즌|감동)|반응|체험|처음|첫|놀란|충격|감동", re.I)
# 영어 강의·회화 교재형 영상은 외국인의 경험이 아니므로 제외 (수집과 사이트 분류에 모두 적용)
EXCLUDE = r"영어 ?회화|회화 표현|english (lesson|conversation|phrases)|learn english|영어 ?공부|한국어 ?(강의|수업)|korean lesson|learn korean|일본어 ?(강의|수업|회화)|japanese (lesson|class|course|conversation|phrases)|learn japanese|keigo lesson|日本語.{0,4}(講座|レッスン)"
EXCLUDE_RE = re.compile(EXCLUDE, re.I)
PROVENANCE_TOP = 0 if "--jp" in sys.argv else 5  # (일본 버전은 검색 순위만으로 꼭지를 붙이지 않고 제목 규칙이 맞을 때만 분류한다 — Codex 검토 반영)꼭지별 영어 검색 결과 상위 몇 개를, 제목에 규칙 단어가 없어도 그 꼭지로 인정할지
PATTERNS = []  # [(갈래 인덱스, 꼭지 이름, 컴파일된 규칙)]
for _gi, (_c, _n, _items) in enumerate(GROUPS):
    for _name, _rule, _q in _items:
        PATTERNS.append((_gi, _name, re.compile(_rule, re.I)))


def classify(title):
    cats, items = [], []
    for gi, name, pat in PATTERNS:
        if pat.search(title):
            items.append(name)
            if GROUPS[gi][0] not in cats:
                cats.append(GROUPS[gi][0])
    return cats, items


def queries():
    """(갈래, 검색어, 정렬들, 꼭지 이름 또는 None). 꼭지 이름이 있는 검색은 상위 결과를 그 꼭지로 인정한다."""
    qs = []
    for cat, _note, items in GROUPS:
        for name, _rule, en in items:
            qs.append((cat, en, SORTS[:1], name))
            qs.append((cat, "외국인 " + re.sub(r"[()+·\"]", " ", name).strip(), SORTS[:1], name))
        qs.append((cat, "외국인 " + re.sub(r"[·]", " ", cat.split(" ", 1)[1]) + " " + COUNTRY + " 반응", SORTS, None))
    return qs


def check():
    counts = [len(g[2]) for g in GROUPS]
    ok = counts == EXPECT
    print("갈래별 꼭지 수", counts, "합계", sum(counts), "(기대 140 일치)" if ok and sum(counts) == 140 else "<< 슬라이드와 다름")
    for cat, _n, items in GROUPS:
        for name, rule, en in items:
            re.compile(rule, re.I)
            for m in re.finditer(r"\\b", rule):  # JS 의 \b 는 한글을 단어 문자로 보지 않으므로, 한글 바로 옆에는 쓰지 않는다
                before = rule[:m.start()].rstrip("?)")[-1:]   # 바로 앞 글자 (수량자 ? 와 닫는 괄호는 건너뜀)
                after = rule[m.end():][:1]                      # 바로 뒤 글자
                bad = lambda ch: ch not in ("", "|", "(", ")", "?") and not ch.isascii()
                assert not bad(before) and not bad(after), "한글 옆 \\b 금지: " + name
    return ok and sum(counts) == 140


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    if not check():
        print("꼭지 수가 슬라이드와 달라 중단합니다 (check 참고)")
        sys.exit(1)
    if "--refilter" in sys.argv:   # 검색 없이, 저장된 결과를 현재 규칙으로 다시 걸러 낸다 (규칙·판별을 고친 뒤 빠르게 반영)
        kc, ki = ("jg_cats", "jg_items") if JP else ("g_cats", "g_items")
        txt = open(OUT, encoding="utf-8").read()
        saved = json.loads(re.search(r"window\.GLOBAL_ITEMS\w*=(\[.*\]);", txt, re.S).group(1))
        kept = []
        for it in saved:
            t = it["title"]
            cats, items = classify(t)
            if not cats or EXCLUDE_RE.search(t) or not any(w in t.lower() for w in WORDS):
                continue
            it[kc], it[ki] = cats, items
            kept.append(it)
        topics = [{"cat": c, "note": n, "items": [{"name": nm, "rule": r} for nm, r, _q in its]} for c, n, its in GROUPS]
        sfx = "_JP" if JP else ""
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("window.GLOBAL_EXCLUDE=%s;\nwindow.GLOBAL_TOPICS%s=%s;\nwindow.GLOBAL_ITEMS%s=%s;\n" % (
                json.dumps(EXCLUDE, ensure_ascii=False), sfx, json.dumps(topics, ensure_ascii=False), sfx, json.dumps(kept, ensure_ascii=False)))
        print(f"다시 거름: {len(saved)}개 → {len(kept)}개")
        return
    dry = "--dry" in sys.argv
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    store = {}
    if os.path.exists(STORE):
        try:
            with open(STORE, encoding="utf-8") as f:
                store = json.load(f)
        except (OSError, json.JSONDecodeError):
            store = {}

    def run(job):
        _cat, q, sorts, _item = job
        out = []
        for sp in sorts:
            out += ew.search(q, sp)
        return out

    cat_of = {name: g[0] for g in GROUPS for name, _r, _q in g[2]}
    jobs = queries()
    found = {}
    with ThreadPoolExecutor(4) as ex:
        for job, results in zip(jobs, ex.map(run, jobs)):
            item = job[3]
            for rank, v in enumerate(results):
                title = v["title"]
                cats, items = classify(title)
                if item and rank < PROVENANCE_TOP:  # 이 꼭지를 찾으려고 한 검색의 상위 결과는, 제목에 단어가 없어도 그 꼭지로 인정
                    if item not in items:
                        items.append(item)
                    if cat_of[item] not in cats:
                        cats.append(cat_of[item])
                if v["age_h"] is None or not cats or EXCLUDE_RE.search(title):
                    continue
                hangul = bool(re.search(r"[가-힣]", title + v["channel"]))
                if not (any(w in title.lower() for w in WORDS) or (hangul and not JP)):
                    continue  # 한국(일본 버전은 일본)이 주제인 영상만. 일본 버전은 한글 제목만으로는 일본 영상이라 보지 않고 제목에 일본 표현이 있어야 한다
                if not (FOREIGN_VIEW.search(title) or not hangul):
                    continue  # 외국인 시선(사용·경험·반응)이 드러나거나, 외국인 채널이 올린 영상
                if v["duration_sec"] is not None and v["duration_sec"] < MIN_SEC:
                    continue  # 쇼츠 제외 (길이를 모르면 유지)
                if re.search(r"official (music )?video|lyrics|north korea|pyongyang", title.lower()):
                    continue
                prev = found.get(v["id"])
                if prev:  # 여러 검색에 걸린 영상은 꼭지를 합친다
                    prev["g_items"] += [i for i in items if i not in prev["g_items"]]
                    prev["g_cats"] += [c for c in cats if c not in prev["g_cats"]]
                else:
                    v.update(g_cats=cats, g_items=items)
                    found[v["id"]] = v
    print(f"검색어 {len(jobs)}개 → 후보 영상 {len(found)}개")
    ids = sorted({v["channel_id"] for v in found.values()})
    with ThreadPoolExecutor(6) as ex:
        subs = dict(zip(ids, ex.map(ew.channel_subs, ids)))
    items = [{"id": v["id"], "title": v["title"], "channel": v["channel"], "channel_id": v["channel_id"], "subs": subs.get(v["channel_id"]),
              "views": v["views"], "country": COUNTRY, "section": "global_topic_jp" if JP else "global_topic", ("jg_cats" if JP else "g_cats"): v["g_cats"], ("jg_items" if JP else "g_items"): v["g_items"],
              "age_text": v["age_text"], "length": v["length"], "duration_sec": v["duration_sec"],
              "published": (now - timedelta(hours=v["age_h"])).strftime("%Y-%m-%d"), "first_seen": store.get(v["id"], today)}
             for v in found.values()]
    items.sort(key=lambda x: (x["first_seen"], x["views"]), reverse=True)
    items = items[:MAX_ITEMS]
    kc, ki = ("jg_cats", "jg_items") if JP else ("g_cats", "g_items")
    by_cat = {g[0]: sum(g[0] in i[kc] for i in items) for g in GROUPS}
    print(f"수집 {len(items)}개", by_cat)
    if dry:
        for i in items[:15]:
            print(f"  {','.join(i[ki])[:22]:22} {i['length'] or '-':>8} 조회 {i['views']:>9,} {i['channel']} | {i['title'][:42]}")
        return
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({i["id"]: i["first_seen"] for i in items}, f, ensure_ascii=False)
    topics = [{"cat": c, "note": n, "items": [{"name": nm, "rule": r} for nm, r, _q in its]} for c, n, its in GROUPS]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        sfx = "_JP" if JP else ""
        f.write("window.GLOBAL_EXCLUDE=%s;\nwindow.GLOBAL_TOPICS%s=%s;\nwindow.GLOBAL_ITEMS%s=%s;\n" % (
            json.dumps(EXCLUDE, ensure_ascii=False), sfx, json.dumps(topics, ensure_ascii=False), sfx, json.dumps(items, ensure_ascii=False)))
    print("저장:", os.path.relpath(OUT, BASE))


if __name__ == "__main__":
    main()
