/*
 * 555电影 —— 苹果CMS V10 站点，drpy2 规则
 *
 * 域名自适应：555 用发布页 https://www.555dyy.top 承载入口，
 * 真实站点域名放在页面 #domainData 的 data-info（base64 JSON）里，
 * 形如 {"site_main":"www.555k02.com","site_1":"www.5k27.top",...}。
 * hostJs 每次加载自动读取，域名换了不用改规则。
 *
 * 页面结构（实测 2026-11）：
 *   列表 /vodshow/{tid}-{area}-{by}-{class}-{lang}----{page}---{year}.html
 *        → a.module-poster-item > .module-poster-item-title / .module-item-note / img[data-original]
 *   搜索 /vodsearch/{wd}----------{page}---.html
 *        → .module-card-item > .module-card-item-title / .module-item-note / img[data-original]
 *   详情 /voddetail/{id}.html
 *        → .module-play-list 每组一条线路，取集数最多的那条
 *   播放 /vodplay/{id}-{sid}-{nid}.html
 *        → <script>var player_aaaa={...,"url":"https://.../index.m3u8",...}</script>
 *
 * 播放地址策略：单集解析约 0.7s，46 集要 34s 会超时。
 * 因此前 12 集直连 m3u8（秒开），其余保留播放页地址交给客户端嗅探。
 */

var FLT = [
    {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"大陆", "v": "大陆"},{"n":"香港", "v": "香港"},{"n":"台湾", "v": "台湾"},{"n":"美国", "v": "美国"},{"n":"日本", "v": "日本"},{"n":"韩国", "v": "韩国"},{"n":"英国", "v": "英国"},{"n":"法国", "v": "法国"},{"n":"德国", "v": "德国"},{"n":"印度", "v": "印度"},{"n":"泰国", "v": "泰国"},{"n":"丹麦", "v": "丹麦"},{"n":"瑞典", "v": "瑞典"},{"n":"巴西", "v": "巴西"},{"n":"加拿大", "v": "加拿大"},{"n":"俄罗斯", "v": "俄罗斯"},{"n":"意大利", "v": "意大利"},{"n":"比利时", "v": "比利时"},{"n":"爱尔兰", "v": "爱尔兰"},{"n":"西班牙", "v": "西班牙"},{"n":"澳大利亚", "v": "澳大利亚"}]},
    {"key":"class","name":"类型","value":[{"n":"全部","v":""},{"n":"Netflix", "v": "Netflix"},{"n":"仙侠", "v": "仙侠"},{"n":"剧情", "v": "剧情"},{"n":"科幻", "v": "科幻"},{"n":"动作", "v": "动作"},{"n":"喜剧", "v": "喜剧"},{"n":"爱情", "v": "爱情"},{"n":"冒险", "v": "冒险"},{"n":"儿童", "v": "儿童"},{"n":"歌舞", "v": "歌舞"},{"n":"音乐", "v": "音乐"},{"n":"奇幻", "v": "奇幻"},{"n":"动画", "v": "动画"},{"n":"恐怖", "v": "恐怖"},{"n":"惊悚", "v": "惊悚"},{"n":"丧尸", "v": "丧尸"},{"n":"战争", "v": "战争"},{"n":"传记", "v": "传记"},{"n":"纪录", "v": "纪录"},{"n":"犯罪", "v": "犯罪"},{"n":"悬疑", "v": "悬疑"},{"n":"西部", "v": "西部"},{"n":"灾难", "v": "灾难"},{"n":"古装", "v": "古装"},{"n":"武侠", "v": "武侠"},{"n":"家庭", "v": "家庭"},{"n":"短片", "v": "短片"},{"n":"校园", "v": "校园"},{"n":"文艺", "v": "文艺"},{"n":"运动", "v": "运动"},{"n":"青春", "v": "青春"},{"n":"同性", "v": "同性"},{"n":"励志", "v": "励志"},{"n":"人性", "v": "人性"},{"n":"美食", "v": "美食"},{"n":"女性", "v": "女性"},{"n":"治愈", "v": "治愈"},{"n":"历史", "v": "历史"},{"n":"真人秀", "v": "真人秀"},{"n":"脱口秀", "v": "脱口秀"}]},
    {"key":"lang","name":"语言","value":[{"n":"全部","v":""},{"n":"英语", "v": "英语"},{"n":"法语", "v": "法语"},{"n":"国语", "v": "国语"},{"n":"粤语", "v": "粤语"},{"n":"日语", "v": "日语"},{"n":"韩语", "v": "韩语"},{"n":"泰语", "v": "泰语"},{"n":"德语", "v": "德语"},{"n":"俄语", "v": "俄语"},{"n":"闽南语", "v": "闽南语"},{"n":"丹麦语", "v": "丹麦语"},{"n":"波兰语", "v": "波兰语"},{"n":"瑞典语", "v": "瑞典语"},{"n":"印地语", "v": "印地语"},{"n":"挪威语", "v": "挪威语"},{"n":"意大利语", "v": "意大利语"},{"n":"西班牙语", "v": "西班牙语"}]},
    {"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2026", "v": "2026"},{"n":"2025", "v": "2025"},{"n":"2024", "v": "2024"},{"n":"2023", "v": "2023"},{"n":"2022", "v": "2022"},{"n":"2021", "v": "2021"},{"n":"2020", "v": "2020"},{"n":"2019", "v": "2019"},{"n":"2018", "v": "2018"},{"n":"2017", "v": "2017"},{"n":"2016", "v": "2016"},{"n":"2015", "v": "2015"},{"n":"2014", "v": "2014"},{"n":"2013", "v": "2013"},{"n":"2012", "v": "2012"},{"n":"2011", "v": "2011"},{"n":"2010", "v": "2010"},{"n":"2009", "v": "2009"},{"n":"2008", "v": "2008"},{"n":"2007", "v": "2007"},{"n":"2006", "v": "2006"},{"n":"2005", "v": "2005"},{"n":"2004", "v": "2004"},{"n":"2003", "v": "2003"},{"n":"2002", "v": "2002"},{"n":"2001", "v": "2001"},{"n":"2000", "v": "2000"},{"n":"90年代", "v": "90年代"},{"n":"80年代", "v": "80年代"},{"n":"70年代", "v": "70年代"},{"n":"更早", "v": "更早"}]},
    {"key":"by","name":"排序","value":[{"n":"时间","v":"time"},{"n":"人气","v":"hits"},{"n":"评分","v":"score"}]}
];

var rule = {
    title: '555电影',
    host: 'https://www.555k02.com',
    hostJs: 'try{let h=request("https://www.555dyy.top",{headers:{"User-Agent":PC_UA}});let m=h.match(/id="domainData"[^>]*data-info="([^"]+)"/);if(m){let b=m[1].replace(/-/g,"+").replace(/_/g,"/");let d=JSON.parse(base64Decode(b));if(d&&d.site_main){HOST="https://"+d.site_main;print("555电影 当前域名: "+HOST)}}}catch(e){print("555电影 发布页解析跳过: "+e)}',
    homeUrl: '/',
    url: '/vodshow/fyclass--------fypage---.html',
    searchUrl: '/vodsearch/**----------fypage---.html',
    detailUrl: '/voddetail/fyid.html',
    searchable: 2,
    quickSearch: 1,
    filterable: 1,
    headers: {'User-Agent': 'MOBILE_UA'},
    timeout: 9000,
    class_name: '电影&连续剧&综艺&动漫&短剧',
    class_url: '1&2&3&4&126',
    推荐: '.module-poster-item;.module-poster-item-title&&Text;img&&data-original;.module-item-note&&Text;&&href',
    一级: '.module-poster-item;.module-poster-item-title&&Text;img&&data-original;.module-item-note&&Text;&&href',
    搜索: '.module-card-item;.module-card-item-title&&Text;img&&data-original;.module-item-note&&Text;a&&href',
    二级: 'js:let html=request(input);let H=HOST;let _t=function(s){try{return pdfh(html,s)}catch(e){return ""}};let nm=_t(".module-info-heading&&h1&&Text")||_t("h1&&Text");let pic=_t(".module-info-poster&&img&&data-original")||_t(".module-info-poster&&img&&src")||_t(".module-item-pic&&img&&data-original");let desc=_t(".module-info-introduction-content&&Text");let panels=pdfa(html,".module-play-list");let best=[];for(let i=0;i<panels.length;i++){try{let ls=pdfa(panels[i],"a.module-play-list-link");if(ls.length>best.length)best=ls}catch(e){}}if(best.length==0){best=pdfa(html,"a.module-play-list-link")}let urls=[];for(let i=0;i<best.length;i++){let it=best[i];let cn="";let u="";try{cn=(pdfh(it,"span&&Text")||pdfh(it,"Text")||"").trim()}catch(e){}try{u=pd(it,"href")}catch(e){}if(!u)continue;if(u.indexOf("http")!==0)u=H+u;let real=u;if(i<12&&u.indexOf("/vodplay/")>-1){try{let ph=request(u);let m=ph.match(/player_[a-zA-Z0-9_]+\s*=\s*(\{[\s\S]*?\})\s*<\/script>/);if(m){let j=JSON.parse(m[1]);if(j&&j.url&&/^https?:/.test(j.url))real=j.url}}catch(e){}}urls.push((cn||("第"+(i+1)+"集"))+"$"+real)}VOD={vod_id:input,vod_name:nm,vod_pic:pic,vod_content:desc,vod_play_from:"555",vod_play_url:urls.join("#")};',
    filter_url: '/vodshow/fyclass-{{fl.area}}-{{fl.by}}-{{fl.class}}-{{fl.lang}}----fypage---{{fl.year}}.html'
};

rule.filter = {'1': FLT, '2': FLT, '3': FLT, '4': FLT, '126': FLT};
