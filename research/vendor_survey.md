# 会議録検索システム ベンダー採用自治体調査

調査日: 2026-06-11

## 調査方針と限界

- 目的は、全国展開時に「自治体別スクレイパー」ではなく「ベンダー別アダプタ」でどこまで横展開できるかを見積もること。
- 通常の検索エンジン `site:` 検索は、Bing RSS でも条件外結果が多く、Google/DuckDuckGo はブロックやノイズが多かったため、主に以下で補完した。
  - Common Crawl CDX Index: `ssp.kaigiroku.net` と `www.kensakusystem.jp` のクロール済みURLから tenant を抽出。
  - Cert Spotter CT API: `*.dbsr.jp` の証明書SANから host を抽出。
  - 代表URLの軽い確認: 鳥取県内の既知 `kensakusystem.jp/{tenant}/` の title / link のみ確認。
- 自治体サイト本体への大量アクセスはしていない。DB-Search は `https://www.dbsr.jp/robots.txt` が `Disallow: /` のため、本体ページの巡回確認はしていない。
- 件数は公式導入数ではなく、外部インデックスから確認できた下限寄りの概数。sample/test/counter系ホストは除外した。

## 1. ベンダー別サマリー

| 系統 | 確認件数 | 主な根拠 | 都道府県分布の特徴 | アダプタ化見通し |
| --- | ---: | --- | --- | --- |
| DB-Search系 (`*.dbsr.jp`) | 約175自治体相当 | Cert Spotter CT APIで2026年発行証明書のSANを正規化 | 東京25、宮城16、福岡10、神奈川9、富山8、愛知8など。鳥取は県議会・鳥取市を確認 | 高い。host命名規則が強いが、`www/net/www2/net2/sec/pre` など入口差分の吸収が必要 |
| kensakusystem 新系統 (`ssp.kaigiroku.net`) | 72 tenant確認 | Common Crawl 2026/2025 index | 埼玉9、大阪6、愛知4、大分4、東京4、徳島3など。県議会も複数 | 高い。`/tenant/{tenant}/` が共通で、画面・詳細URLのパターンもかなり揃う |
| kensakusystem 旧/併設系統 (`www.kensakusystem.jp`) | 会議録系24前後、VOD含むrootは57 | Common Crawl + 鳥取3市の代表確認 | 鳥取県内は米子・倉吉・境港が `/{tenant}/` で稼働。全国側は録画配信 `*-vod` が混在 | 中。会議録検索と録画配信の切り分けが必要。古いShift_JISページと `cgi-bin3/*.exe?Code=...` を扱う |
| Sophia / discuss等 | 今回は概数化できず | 検索語では確度の高い共通公開ドメインを確認できず | 個別自治体導線ベースの再調査が必要 | 3個目以降の候補。まずはDB-Search / kensakusystemで十分な母数がある |

## 2. DB-Search系 採用候補リスト

根拠URL: `https://api.certspotter.com/v1/issuances?domain=dbsr.jp&include_subdomains=true&expand=dns_names`

正規化ルール:

- `www.`, `net.`, `www2.`, `net2.`, `sec.`, `pre.`, `web.`, `dww.`, `mww.` は入口差分として除外して同一自治体に寄せた。
- `*.sample.dbsr.jp`, `*.test.dbsr.jp`, `counter*.dbsr.jp`, `www.dbsr.jp` は除外した。
- URLは原則 `https://{host}/`。本体 robots が `Disallow: /` のため、ここではページ内容の取得確認はしていない。

### 都道府県分布

| 都道府県 | 件数 |
| --- | ---: |
| 東京 | 25 |
| 宮城 | 16 |
| 福岡 | 10 |
| 神奈川 | 9 |
| 富山 | 8 |
| 愛知 | 8 |
| 千葉 | 7 |
| 茨城 | 6 |
| 奈良 | 5 |
| 佐賀 | 5 |
| 石川 | 5 |
| 静岡 | 5 |
| 長崎 / 福井 / 鹿児島 / 香川 | 各4 |
| 群馬 / 大阪 / 岐阜 / 青森 / 兵庫 / 福島 / 京都 / 山形 | 各3 |
| 三重 / 山口 / 広島 / 山梨 / 埼玉 / 滋賀 / 宮崎 / 鳥取 / 熊本 | 各2 |
| 愛媛 / 島根 / 岡山 / 大分 / 徳島 / 北海道 / 秋田 / 高知 | 各1 |

### 採用候補リスト

- 愛知: 愛知県議会 `www.pref.aichi.dbsr.jp`; あま市 `www.city.ama.aichi.dbsr.jp`; 碧南市 `net.city.hekinan.aichi.dbsr.jp`; 西尾市 `www.city.nishio.aichi.dbsr.jp`; 新城市 `www.city.shinshiro.aichi.dbsr.jp`; 豊明市 `www.city.toyoake.aichi.dbsr.jp`; 津島市 `www.city.tsushima.aichi.dbsr.jp`; 東郷町 `www.town.togo.aichi.dbsr.jp`
- 秋田: 三種町 `www.town.mitane.akita.dbsr.jp`
- 青森: 青森県議会 `www.pref.aomori.dbsr.jp`; 青森市 `www.city.aomori.aomori.dbsr.jp`; 六ヶ所村 `www.vill.rokkasho.aomori.dbsr.jp`
- 千葉: 千葉市 `net.city.chiba.chiba.dbsr.jp`; 木更津市 `www.city.kisarazu.chiba.dbsr.jp`; 南房総市 `www.city.minamiboso.chiba.dbsr.jp`; 山武市 `www.city.sammu.chiba.dbsr.jp`; 白井市 `www.city.shiroi.chiba.dbsr.jp`; 多古町 `net.town.tako.chiba.dbsr.jp`; 長生村 `www.vill.chosei.chiba.dbsr.jp`
- 愛媛: 今治市 `net.city.imabari.ehime.dbsr.jp`
- 福井: 福井県議会 `www.pref.fukui.dbsr.jp`; 鯖江市 `www.city.sabae.fukui.dbsr.jp`; 坂井市 `www.city.sakai.fukui.dbsr.jp`; 敦賀市 `net.city.tsuruga.fukui.dbsr.jp`
- 福岡: 福岡県議会 `www.pref.fukuoka.dbsr.jp`; 福岡市 `www.city.fukuoka.fukuoka.dbsr.jp`; 筑紫野市 `www.city.chikushino.fukuoka.dbsr.jp`; 糸島市 `www.city.itoshima.fukuoka.dbsr.jp`; 春日市 `www.city.kasuga.fukuoka.dbsr.jp`; 古賀市 `www.city.koga.fukuoka.dbsr.jp`; 宮若市 `www.city.miyawaka.fukuoka.dbsr.jp`; 宗像市 `www.city.munakata.fukuoka.dbsr.jp`; 大野城市 `www.city.onojo.fukuoka.dbsr.jp`; 川崎町 `www.town.kawasaki.fukuoka.dbsr.jp`
- 福島: 喜多方市 `www.city.kitakata.fukushima.dbsr.jp`; 石川町 `www.town.ishikawa.fukushima.dbsr.jp`; 桑折町 `www.town.koori.fukushima.dbsr.jp`
- 岐阜: 岐阜市 `net.city.gifu.gifu.dbsr.jp`; 可児市 `www.city.kani.gifu.dbsr.jp`; 大垣市 `www.city.ogaki.gifu.dbsr.jp`
- 群馬: 伊勢崎市 `www.city.isesaki.gunma.dbsr.jp`; 前橋市 `sec.city.maebashi.gunma.dbsr.jp`; 沼田市 `www.city.numata.gunma.dbsr.jp`
- 広島: 広島県議会 `www.pref.hiroshima.dbsr.jp`; 廿日市市 `www.city.hatsukaichi.hiroshima.dbsr.jp`
- 北海道: 音更町 `www.town.otofuke.hokkaido.dbsr.jp`
- 兵庫: 神戸市 `www.city.kobe.hyogo.dbsr.jp`; 養父市 `www.city.yabu.hyogo.dbsr.jp`; 香美町 `www.town.kami.hyogo.dbsr.jp`
- 茨城: 茨城県議会 `www.pref.ibaraki.dbsr.jp`; 日立市 `www.city.hitachi.ibaraki.dbsr.jp`; 常陸太田市 `www.city.hitachiota.ibaraki.dbsr.jp`; 石岡市 `www.city.ishioka.ibaraki.dbsr.jp`; 常総市 `www.city.joso.ibaraki.dbsr.jp`; 牛久市 `www.city.ushiku.ibaraki.dbsr.jp`
- 石川: 羽咋市 `net.city.hakui.ishikawa.dbsr.jp`; かほく市 `www.city.kahoku.ishikawa.dbsr.jp`; 小松市 `net.city.komatsu.ishikawa.dbsr.jp`; 能美市 `www.city.nomi.ishikawa.dbsr.jp`; 珠洲市 `www.city.suzu.ishikawa.dbsr.jp`
- 香川: 香川県議会 `www.pref.kagawa.dbsr.jp`; 東かがわ市 `www.city.higashikagawa.kagawa.dbsr.jp`; 三豊市 `www.city.mitoyo.kagawa.dbsr.jp`; さぬき市 `www.city.sanuki.kagawa.dbsr.jp`
- 鹿児島: 鹿児島県議会 `www.pref.kagoshima.dbsr.jp`; 阿久根市 `www.city.akune.kagoshima.dbsr.jp`; 伊佐市 `www.city.isa.kagoshima.dbsr.jp`; 西之表市 `www.city.nishinoomote.kagoshima.dbsr.jp`
- 神奈川: 厚木市 `www.city.atsugi.kanagawa.dbsr.jp`; 秦野市 `www.city.hadano.kanagawa.dbsr.jp`; 平塚市 `net.city.hiratsuka.kanagawa.dbsr.jp`; 伊勢原市 `www.city.isehara.kanagawa.dbsr.jp`; 南足柄市 `www.city.minamiashigara.kanagawa.dbsr.jp`; 中井町 `www.town.nakai.kanagawa.dbsr.jp`; 二宮町 `www.town.ninomiya.kanagawa.dbsr.jp`; 寒川町 `www.town.samukawa.kanagawa.dbsr.jp`; 湯河原町 `net.town.yugawara.kanagawa.dbsr.jp`
- 高知: 香南市 `www.city.konan.kochi.dbsr.jp`
- 熊本: 荒尾市 `www.city.arao.kumamoto.dbsr.jp`; 長洲町 `net.town.nagasu.kumamoto.dbsr.jp`
- 京都: 京都府議会 `www.pref.kyoto.dbsr.jp`; 木津川市 `www.city.kizugawa.kyoto.dbsr.jp`; 八幡市 `www.city.yawata.kyoto.dbsr.jp`
- 三重: 桑名市 `www.city.kuwana.mie.dbsr.jp`; 四日市市 `www.city.yokkaichi.mie.dbsr.jp`
- 宮城: 仙台市 `net.city.sendai.miyagi.dbsr.jp`; 岩沼市 `www.city.iwanuma.miyagi.dbsr.jp`; 角田市 `www.city.kakuda.miyagi.dbsr.jp`; 気仙沼市 `www.city.kesennuma.miyagi.dbsr.jp`; 栗原市 `www.city.kurihara.miyagi.dbsr.jp`; 名取市 `www.city.natori.miyagi.dbsr.jp`; 白石市 `www.city.shiroishi.miyagi.dbsr.jp`; 多賀城市 `www.city.tagajo.miyagi.dbsr.jp`; 登米市 `www.city.tome.miyagi.dbsr.jp`; 富谷市 `www.city.tomiya.miyagi.dbsr.jp`; 美里町 `www.town.misato.miyagi.dbsr.jp`; 大河原町 `www.town.ogawara.miyagi.dbsr.jp`; 女川町 `www.town.onagawa.miyagi.dbsr.jp`; 柴田町 `www.town.shibata.miyagi.dbsr.jp`; 亘理町 `www.town.watari.miyagi.dbsr.jp`; 山元町 `www.town.yamamoto.miyagi.dbsr.jp`
- 宮崎: 宮崎市 `www.city.miyazaki.miyazaki.dbsr.jp`; 日南市 `www.city.nichinan.miyazaki.dbsr.jp`
- 長崎: 長崎市 `net.city.nagasaki.nagasaki.dbsr.jp`; 諫早市 `www.city.isahaya.nagasaki.dbsr.jp`; 松浦市 `www.city.matsuura.nagasaki.dbsr.jp`; 島原市 `www.city.shimabara.nagasaki.dbsr.jp`
- 奈良: 生駒市 `net.city.ikoma.nara.dbsr.jp`; 橿原市 `net.city.kashihara.nara.dbsr.jp`; 葛城市 `net.city.katsuragi.nara.dbsr.jp`; 桜井市 `www.city.sakurai.nara.dbsr.jp`; 大和高田市 `www.city.yamatotakada.nara.dbsr.jp`
- 大分: 宇佐市 `www.city.usa.oita.dbsr.jp`
- 岡山: 新見市 `www.city.niimi.okayama.dbsr.jp`
- 大阪: 枚方市 `net.city.hirakata.osaka.dbsr.jp`; 岸和田市 `net.city.kishiwada.osaka.dbsr.jp`; 泉南市 `www.city.sennan.osaka.dbsr.jp`
- 佐賀: 佐賀県議会 `www.pref.saga.dbsr.jp`; 神埼市 `www.city.kanzaki.saga.dbsr.jp`; 上峰町 `www.town.kamimine.saga.dbsr.jp`; みやき町 `www.town.miyaki.saga.dbsr.jp`; 吉野ヶ里町 `www.town.yoshinogari.saga.dbsr.jp`
- 埼玉: 川越市 `www.city.kawagoe.saitama.dbsr.jp`; 松伏町 `www.town.matsubushi.saitama.dbsr.jp`
- 滋賀: 彦根市 `www.city.hikone.shiga.dbsr.jp`; 愛荘町 `www.town.aisho.shiga.dbsr.jp`
- 島根: 島根県議会 `www.pref.shimane.dbsr.jp`
- 静岡: 静岡市 `www.city.shizuoka.shizuoka.dbsr.jp`; 袋井市 `www.city.fukuroi.shizuoka.dbsr.jp`; 焼津市 `www.city.yaizu.shizuoka.dbsr.jp`; 長泉町 `www.town.nagaizumi.shizuoka.dbsr.jp`; 清水町 `www.town.shimizu.shizuoka.dbsr.jp`
- 徳島: 小松島市 `www.city.komatsushima.tokushima.dbsr.jp`
- 東京: 東京都議会 `dww.metro.tokyo.dbsr.jp`; 文京区 `www.city.bunkyo.tokyo.dbsr.jp`; 千代田区 `www.city.chiyoda.tokyo.dbsr.jp`; 府中市 `www.city.fuchu.tokyo.dbsr.jp`; 福生市 `www.city.fussa.tokyo.dbsr.jp`; 八王子市 `www.city.hachioji.tokyo.dbsr.jp`; 羽村市 `www.city.hamura.tokyo.dbsr.jp`; 東久留米市 `www.city.higashikurume.tokyo.dbsr.jp`; 日野市 `www.city.hino.tokyo.dbsr.jp`; 稲城市 `www.city.inagi.tokyo.dbsr.jp`; 板橋区 `www.city.itabashi.tokyo.dbsr.jp`; 小金井市 `www.city.koganei.tokyo.dbsr.jp`; 国分寺市 `www.city.kokubunji.tokyo.dbsr.jp`; 狛江市 `www.city.komae.tokyo.dbsr.jp`; 江東区 `www.city.koto.tokyo.dbsr.jp`; 国立市 `www.city.kunitachi.tokyo.dbsr.jp`; 三鷹市 `net.city.mitaka.tokyo.dbsr.jp`; 武蔵野市 `www.city.musashino.tokyo.dbsr.jp`; 西東京市 `www.city.nishitokyo.tokyo.dbsr.jp`; 品川区 `net.city.shinagawa.tokyo.dbsr.jp`; 多摩市 `www.city.tama.tokyo.dbsr.jp`; あきる野市 `net.city.akiruno.tokyo.dbsr.jp`; 日の出町 `www.town.hinode.tokyo.dbsr.jp`; 奥多摩町 `www.town.okutama.tokyo.dbsr.jp`; 檜原村 `www.vill.hinohara.tokyo.dbsr.jp`
- 鳥取: 鳥取県議会 `www.pref.tottori.dbsr.jp`; 鳥取市 `www.city.tottori.tottori.dbsr.jp`
- 富山: 富山県議会 `web.pref.toyama.dbsr.jp`; 高岡市 `www.city.takaoka.toyama.dbsr.jp`; 富山市 `net.city.toyama.toyama.dbsr.jp`; 魚津市 `www.city.uozu.toyama.dbsr.jp`; 朝日町 `www.town.asahi.toyama.dbsr.jp`; 上市町 `www.town.kamiichi.toyama.dbsr.jp`; 入善町 `www.town.nyuzen.toyama.dbsr.jp`; 立山町 `www.town.tateyama.toyama.dbsr.jp`
- 山形: 上山市 `www.city.kaminoyama.yamagata.dbsr.jp`; 小国町 `www.town.oguni.yamagata.dbsr.jp`; 高畠町 `www.town.takahata.yamagata.dbsr.jp`
- 山口: 光市 `www.city.hikari.yamaguchi.dbsr.jp`; 山口市 `www.city.yamaguchi.yamaguchi.dbsr.jp`
- 山梨: 山梨県議会 `kaigiroku.pref.yamanashi.dbsr.jp`; 甲府市 `sec.city.kofu.yamanashi.dbsr.jp`

## 3. kensakusystem系 採用候補リスト

### 3.1 `ssp.kaigiroku.net`

根拠URL:

- `https://index.commoncrawl.org/CC-MAIN-2026-21-index?url=kaigiroku.net/*&matchType=domain&output=json&fl=url&collapse=urlkey&limit=5000`
- `https://index.commoncrawl.org/CC-MAIN-2025-51-index?url=ssp.kaigiroku.net/*&output=json&fl=url&collapse=urlkey&limit=5000`

採用候補リスト:

- 北海道: 恵庭市 `eniwa`; 函館市 `hakodate`
- 秋田: 秋田県議会 `prefakita`
- 宮城: 宮城県議会 `prefmiyagi`; 大崎市 `oosaki`
- 福島: 会津若松市 `aizuwakamatsu`; 棚倉町 `tanagura`
- 茨城: 古河市 `koga`
- 栃木: 真岡市 `moka`
- 群馬: みどり市 `midori`; 富岡市 `tomioka`
- 埼玉: 上尾市 `ageo`; 飯能市 `hanno`; 神川町/上川町等 `kamikawa`（自治体名要確認）; 鴻巣市 `kounosu`; 久喜市 `kuki`; 桶川市 `okegawa`; さいたま市 `saitama`; 白岡市 `shiraoka`; 吉見町 `yoshimi`
- 千葉: 我孫子市 `abiko`; 市原市 `ichihara`; 市川市 `ichikawa`
- 東京: 小平市 `kodaira`; 練馬区 `nerima`; 青梅市 `ome`; 渋谷区 `shibuya`
- 神奈川: 小田原市 `odawara`
- 新潟: 新潟県議会 `prefniigata`; 阿賀町 `aga`
- 石川: 金沢市 `kanazawa`
- 山梨: 市川三郷町 `ichikawamisato`
- 長野: 佐久市 `saku`
- 岐阜: 岐阜県議会 `prefgifu`
- 静岡: 浜松市 `hamamatsu`; 伊豆市 `izu`
- 愛知: 蒲郡市 `gamagori`; 半田市 `handa`; 豊橋市 `toyohashi`; 豊山町 `toyoyama`
- 滋賀: 甲賀市 `koka`
- 京都: 亀岡市 `kameoka`
- 大阪: 大阪府議会 `prefosaka`; 大阪市 `cityosaka`; 柏原市 `kashiwara`; 箕面市 `minoh`; 吹田市 `suita`; 高石市 `takaishi`
- 兵庫: 尼崎市 `amagasaki`; 芦屋市 `ashiya`
- 奈良: 奈良県議会 `prefnara`
- 岡山: 倉敷市 `kurashiki`
- 広島: 三原市 `mihara`; 尾道市 `onomichi`
- 山口: 山口県議会 `prefyamaguchi`; 下松市 `kudamatsu`
- 徳島: 徳島県議会 `tokushimapref`; 阿南市 `anan`; 石井町 `ishii`
- 香川: 観音寺市 `kanonji`
- 高知: 土佐市 `tosa`
- 福岡: 北九州市 `kitakyushu`; 岡垣町 `okagaki`
- 熊本: 熊本県議会 `prefkumamoto`
- 大分: 大分県議会 `prefoita`; 日田市 `hita`; 九重町 `kokonoe`; 臼杵市 `usuki`
- 宮崎: 綾町 `aya`; 門川町 `kadogawa`
- 鹿児島: 鹿屋市 `kanoya`
- 沖縄: 那覇港管理組合議会 `nahaport`

URLは原則 `https://ssp.kaigiroku.net/tenant/{tenant}/`。確認できた代表パスは以下:

- `SpTop.html`
- `MinuteSearch.html` / `SpMinuteSearch.html`
- `MinuteIndex.html`
- `MinuteView.html` / `SpMinuteView.html?council_id=...&schedule_id=...&minute_id=...`
- `MaterialList.html` / `SpMaterial.html`
- `pg/index.html`

### 3.2 `www.kensakusystem.jp`

根拠URL:

- `https://index.commoncrawl.org/CC-MAIN-2026-21-index?url=kensakusystem.jp/*&matchType=domain&output=json&fl=url&collapse=urlkey&limit=2000`
- 鳥取県内の代表URL確認:
  - `https://www.kensakusystem.jp/yonago/`
  - `https://www.kensakusystem.jp/kurayoshi/`
  - `https://www.kensakusystem.jp/sakaiminato/`

Common Crawlで確認したrootは57。うち `*-vod` を除いた会議録候補は21 root、鳥取県内の既知3 rootを加えると24前後。

会議録候補:

- 愛媛県議会 `ehime`
- 印南町 `inami`
- 伊丹市 `itami`
- 鎌倉市 `kamakura`
- 鹿沼市 `kanuma-c`
- 葛飾区 `katsushika`
- 勝山市 `katsuyama-gikai`
- 神戸市会 `kobeshikai`
- 神戸市会委員会 `kobeshikai-committee`
- 合志市 `koshi`
- 真鶴町 `manazuru`
- 守口市 `moriguchi`
- 大井町 `oi`
- 小野市 `ono-c`
- 栗東市 `ritto`
- 三条市 `sanjo`
- たつの市 `tatsuno`
- 東員町 `toin`
- 東海市 `tokai`
- 豊岡市 `toyooka`
- 八街市 `yachimata`
- 米子市 `yonago`
- 倉吉市 `kurayoshi`
- 境港市 `sakaiminato`

鳥取3市のトップページ title:

- 米子市: `米子市議会 会議録検索システム トップページ`
- 倉吉市: `倉吉市議会/会議録検索システム`
- 境港市: `境港市議会/会議録検索システム`

鳥取3市のリンク構造:

- トップ: `https://www.kensakusystem.jp/{tenant}/`
- 閲覧: `cgi-bin3/See.exe?Code={tenant固有コード}`
- 検索: `cgi-bin3/Search2.exe?Code={tenant固有コード}&sTarget=2`
- 文字コード: Shift_JIS / CP932

## 4. 鳥取の次に展開する候補地域

### 第1候補: 宮城県（DB-Search）

- DB-Search候補が16件あり、県内で市・町がまとまっている。
- 東京より自治体タイプのばらつきが小さく、DB-Searchアダプタの初回横展開検証に向く。
- 県議会は `ssp.kaigiroku.net` 側にも見えるため、同一県内でDB-Searchとkensakusystem系の境界検証もできる。

### 第2候補: 東京都（DB-Search）

- DB-Search候補が25件で最大。
- 都議会、特別区、市、町、村が混在するため、アダプタのロバスト性検証には非常に良い。
- 一方で、最初の横展開先としては制度・自治体種別の差分が多く、宮城より調査コストが高そう。

### 第3候補: 埼玉県または大阪府（`ssp.kaigiroku.net`）

- 埼玉は `ssp.kaigiroku.net` 候補が9件で最多。
- 大阪は `prefosaka`, `cityosaka`, `suita`, `minoh`, `takaishi`, `kashiwara` など、府・政令市・市が揃う。
- kensakusystem新系統の adapter を作るなら、鳥取3市の旧系統とは別に、埼玉/大阪で `ssp.kaigiroku.net` の実装妥当性を測るのが効率的。

## 5. URLパターン分析

### DB-Search系

観測したhost命名は以下が中心:

- `www.pref.{pref}.dbsr.jp`
- `www.city.{city}.{pref}.dbsr.jp`
- `www.town.{town}.{pref}.dbsr.jp`
- `www.vill.{village}.{pref}.dbsr.jp`
- `www.metro.tokyo.dbsr.jp`

入口差分:

- `www` と `net` の両方がある自治体がある。
- `www2`, `net2`, `sec`, `pre`, `web`, `dww`, `mww` も確認した。
- adapter設計では、自治体IDからhostを1つに決め打ちせず、`host_candidates` を持てるようにするのがよい。

注意:

- `www.dbsr.jp/robots.txt` は `Disallow: /`。検索エンジン/CTログによる列挙は可能だが、本体への自動巡回は別途慎重な判断が必要。
- CTログは「証明書が発行されたhost」の証拠であって、「現在ページが公開運用されている」ことの完全な証明ではない。

### `ssp.kaigiroku.net`

URLはかなり規則的:

```text
https://ssp.kaigiroku.net/tenant/{tenant}/
https://ssp.kaigiroku.net/tenant/{tenant}/SpTop.html
https://ssp.kaigiroku.net/tenant/{tenant}/MinuteSearch.html
https://ssp.kaigiroku.net/tenant/{tenant}/SpMinuteSearch.html
https://ssp.kaigiroku.net/tenant/{tenant}/SpMinuteView.html?council_id={id}&schedule_id={id}&minute_id={id}
```

adapter化の見通し:

- tenant差し替えでかなり横展開できる可能性が高い。
- PC/スマホ風の `Minute*` / `SpMinute*` が混在するため、最初から両方を許容する。
- `pg/index.html` のような静的入口もあるため、トップページ探索は複数候補を順番に見る形がよい。

### `www.kensakusystem.jp`

鳥取3市では以下が共通:

```text
https://www.kensakusystem.jp/{tenant}/
https://www.kensakusystem.jp/{tenant}/cgi-bin3/See.exe?Code={code}
https://www.kensakusystem.jp/{tenant}/cgi-bin3/Search2.exe?Code={code}&sTarget=2
```

adapter化の見通し:

- `tenant` はURL pathで共通化できる。
- `Code` はtenantごとの固有値で、トップページから抽出できる。
- Shift_JIS / CP932前提でHTMLを読む必要がある。
- `*-vod` は録画配信で、会議録テキスト検索とは別adapterまたは除外ルールが必要。

## 6. テンプレート設計への示唆

- `minutes_system` は少なくとも `dbsr`, `kensakusystem_legacy`, `kensakusystem_ssp` に分けたほうが実装上は安全。
- councilごとの設定は、自治体固有スクレイパーではなく次の薄い設定で足りる可能性が高い。
  - `vendor`: `dbsr` / `kensakusystem_ssp` / `kensakusystem_legacy`
  - `tenant`: `yonago`, `prefmiyagi`, `city.tottori.tottori` など
  - `base_url` または `host_candidates`
  - `encoding`: `utf-8` / `cp932`
  - `entry_paths`: `SpTop.html`, `MinuteSearch.html`, `cgi-bin3/Search2.exe` など
- 全国展開時の初期優先度は、DB-Search adapterを先に完成させると約170自治体規模の下限母数が見える。次に `ssp.kaigiroku.net` adapterで70自治体以上、最後に `www.kensakusystem.jp` 旧系統とVOD混在を分離するのが自然。

## 参考リンク

- Cert Spotter CT API: https://api.certspotter.com/v1/issuances?domain=dbsr.jp&include_subdomains=true&expand=dns_names
- Common Crawl Index一覧: https://index.commoncrawl.org/collinfo.json
- Common Crawl `ssp.kaigiroku.net` query: https://index.commoncrawl.org/CC-MAIN-2025-51-index?url=ssp.kaigiroku.net/*&output=json&fl=url&collapse=urlkey&limit=5000
- Common Crawl `kaigiroku.net` domain query: https://index.commoncrawl.org/CC-MAIN-2026-21-index?url=kaigiroku.net/*&matchType=domain&output=json&fl=url&collapse=urlkey&limit=5000
- Common Crawl `kensakusystem.jp` query: https://index.commoncrawl.org/CC-MAIN-2026-21-index?url=kensakusystem.jp/*&matchType=domain&output=json&fl=url&collapse=urlkey&limit=2000
- `ssp.kaigiroku.net` robots.txt: https://ssp.kaigiroku.net/robots.txt
- `www.dbsr.jp` robots.txt: https://www.dbsr.jp/robots.txt
- 米子市議会 会議録検索: https://www.kensakusystem.jp/yonago/
- 倉吉市議会 会議録検索: https://www.kensakusystem.jp/kurayoshi/
- 境港市議会 会議録検索: https://www.kensakusystem.jp/sakaiminato/
