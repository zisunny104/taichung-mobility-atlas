# Taichung Mobility Atlas — 01 Traffic Safety

台中市交通安全地圖｜十年回顧（民 105–114 / 2016–2025）

互動式單頁地圖儀表板，以警政署 A1 級道路交通事故公開資料為基礎，呈現台中市十年的死亡事故空間分布、年度趨勢、熱力圖、優先治理路段，以及國道／快速公路／省道幹線疊圖。

## 線上預覽

GitHub Pages：`https://yunching0513.github.io/taichung-mobility-atlas/`

姊妹專案：
- [Taitung Mobility Atlas](https://github.com/yunching0513/taitung-mobility-atlas) — 台東縣
- [Tainan Mobility Atlas](https://github.com/yunching0513/tainan-mobility-atlas) — 台南市
- [Taipei Mobility Atlas](https://github.com/yunching0513/taipei-mobility-atlas) — 台北市
- [Yilan Mobility Atlas](https://github.com/yunching0513/yilan-mobility-atlas) — 宜蘭縣

## 主要觀察（十年累計）

- **1,607 人**在台中市道路上死亡，年均 161 人；2020 年為高峰 211 人
- **弱勢用路人合計 88%**（機車 64% + 行人 18% + 慢車 6%）
- **行人受害比例 18%**，僅次於台北市（34%），遠高於台南（10%）與宜蘭（13%）
- **市區道路占 94%**，但**國道 1 號中部段**有三處熱點
- 鄉鎮死亡前五：**北屯 137、西屯 128、大里 93、清水 80、南屯 80**
- 環中路、市環系統與國道交流道為主要好發節點
- 2018→2019 件數倍增（102→197），疑為通報補強或實際惡化（待查證）

## 資料分類方法

事件以「最弱勢用路人」為類別（行人 > 自行車/慢車 > 機車 > 汽車）；
原始 A1 資料的 P1（肇因主要當事者）保留於 `principal_mode` 欄位。

## 資料來源

- [內政部警政署 A1 級交通事故公開資料](https://www.npa.gov.tw/) 透過 [data.gov.tw](https://data.gov.tw/) 取得
- 幹線道路圖層：**交通部公路局 ROAD_國省道(含快速公路)_1150409**（TWD97/TM2 → WGS84，Douglas-Peucker 15m 簡化）

## 底圖

- 簡潔：[souliong](https://github.com/zisunny104/souliong) 的**紙墨**向量樣式（`basemap/paper-ink.json`），取代原本的 CARTO Positron。
- 道路：[OpenFreeMap](https://openfreemap.org) Liberty 向量樣式，取代原本的 CARTO Voyager。
- 衛星：Esri 影像加 CARTO 地名（未更動）。

向量樣式透過 `maplibre-gl-leaflet` 載入原本的 Leaflet 地圖。資料來自 OpenFreeMap 與 © OpenStreetMap contributors。

## 開發者

吳昀慶 · Designed for 台中市交通安全分析

## 授權

程式碼：MIT。資料：依政府資料開放平臺授權條款。
