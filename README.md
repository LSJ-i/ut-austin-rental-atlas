# UT Rental Atlas · 奥斯汀租房地图

中文、响应式、无需构建的 UT Austin 租房地图。GitHub Pages 可直接托管。

## 功能

- 自定义研究片区地图，APD 近 90 天报案数、密度与相对三档分组。
- West Campus、校园周边及 Far West、Riverside、Lake Austin 等 Shuttle 服务片区。
- Bed、Bath、租金、计价方式、入住日期、状态、Google 评分、家具、SMART、区域及校车筛选。
- 收藏保存在本机；筛选写入 URL 可分享；导出当前筛选 CSV。
- 房源来源、核查日期、资格与费用备注；未来预租和候补默认排除。

## 本地运行

在本文件目录运行 `python -m http.server 8765 --bind 127.0.0.1`，访问 http://127.0.0.1:8765 。不能直接双击 HTML，因为浏览器会阻止本地 JSON 请求。

测试：`node --test tests/model.test.mjs`。

## GitHub Pages

将本目录全部内容（包括 `.github`）放入 GitHub 仓库根目录，默认分支 `main`。在 Settings → Pages → Build and deployment 选择 **GitHub Actions**，然后运行 **Deploy rental atlas**。默认网址为 `https://<username>.github.io/<repository>/`。代码使用相对路径，支持仓库子路径。

可运行 `scripts/publish.ps1 -Repository owner/repo` 完成本地初始化与推送，需要本机 Git 和已登录的 GitHub 写权限。仓库必须先存在。也可以使用 GitHub Desktop 添加现有目录并 Publish repository。

## 数据维护

`data/listings.json` 是有来源的人工核查快照，不是实时库存，不包含全部市场。修改具体记录时更新该条 `checkedAt`，只有实际检查过新资料才更新日期。不要仅因重新部署就改日期。未知起租日写 `null`，不要用核查日代替可入住日。`availableFrom` 是来源公布的日期，不是确认预订。

每条记录：`id,name,address,beds,baths,rent,sqft,status,source,checkedAt,availableFrom,furnished,smart,googleRating,ratingSource,priceBasis,notes,coordinates`。坐标为 `[latitude,longitude]`；未知评分和面积使用 `null`。状态：`available,limited,advertised,needs-confirmation,future,waitlist`。计价：`monthly` 整套月租，`per-bedroom` 每卧室月租，`installment` 每人每期；不直接混淆。Studio 为 `beds:0`。

APD 更新：`python scripts/refresh_crime.py --as-of YYYY-MM-DD`，需网络。脚本成功后原子替换 `data/areas.json`；失败保留旧快照。所有研究区域采用相同窗口和主要罪类集合；按 RIN 去重，除以近似面积，再按本页范围密度三分位分档。窗口不含 as-of 当天。仅发布区域聚合，不发布个案坐标。更新后运行测试，再提交即可部署。这里没有定时自动采集任务。

## 数据解释与来源

- [Austin Police Department CrimeViewer](https://maps.austintexas.gov/arcgis/rest/services/CrimeViewer_new/APD_Reported_Crimes_new/FeatureServer)：层 0–8，主要罪类；暴力子集为 homicide、robbery、aggravated assault。
- [APD 地图说明](https://data.austintexas.gov/stories/s/APD-Crime-Search-Interactive-Map-Guide/6vpz-c8m4/)。未包含 Part II、未报案事件及 [UTPD 独立日志](https://police.utexas.edu/records-reports/daily-crime-log)。
- [UT Shuttle 官方线路](https://parking.utexas.edu/transportation/shuttles) 与 [服务日历](https://utdirect.utexas.edu/apps/fasweb/parking/shuttle-calendar/nlogon/textonly/)。按区域做参考匹配，不是站点覆盖或步行时间计算；具体公寓可能需步行接驳。
- 房源和评分来源保留在每条记录。优先物业官方页面；第三方房源也明确保留来源，不代表物业确认。Google 评分来源如果是聚合展示，其更新时间可能滞后，品牌评分可能不代表单楼。
- 地图 [OpenStreetMap](https://www.openstreetmap.org/copyright)，地理编码 Esri World Geocoding；地图底图请求会发送给 OSM，字体请求会发送给 Google Fonts。
- Leaflet 1.9.4 代码已附带，BSD-2-Clause，见 `assets/vendor/LEAFLET-LICENSE.txt`。

区域为自定义矩形而非官方社区边界，可能重叠。相对报案密度未按人口和访客调整，不是安全承诺、官方治安评级或个人受害概率。当前没有收录某区域房源，不代表该区域无空房。此项目与 UT、APD 或各物业无隶属关系。

备用道路底图：City of Austin [Street Centerline](https://services.arcgis.com/0L95CJ0VTaxqcmED/ArcGIS/rest/services/TRANSPORTATION_street_segment/FeatureServer/0)。可用 python scripts/refresh_roads.py 更新；保留官方源地址。外部 OSM 瓦片不可用时仍可显示本地道路简图。
