# Twitter Trends
### 概要
* Twitterのトレンド情報を定期的に自動取得しDynamoDBに蓄積、トレンドの順位でポイントをつける。毎日夜に集計し結果を自動ツイートするプログラム。

### 処理概要
* getTrends.py -> TwitterAPIを叩きレスポンスのトレンド情報をDynamoDBにインサート
* postTrends.py -> DynamoDBからトレンド情報を取得、集計してhttps://twitter.com/BuzChecker へ投稿する
* AWS lambdaに配置し定期実行。

![構成図](https://user-images.githubusercontent.com/94233243/198821868-0a0ce612-dc51-49cc-bf1d-f6ade28acdcd.png)

-------
### getTrends.pyの処理
#### 1.TwitterAPIからトレンド情報を取得
 URL = https://api.twitter.com/1.1/trends/place.json?id=23424856

id = 23424856 とすることで日本のトレンド情報を取得できる

以下形式のレスポンスが返却される

```
[{'name': '#ポケモンWordle',
'promoted_content': None,
'query': '%23%E3%83%9D%E3%82%B1%E3%83%A2%E3%83%B3Wordle',
'tweet_volume': None,
'url': 'http://twitter.com/search?q=%23%E3%83%9D%E3%82%B1%E3%83%A2%E3%83%B3Wordle'},
{'name': '#帰れマンデー',
'promoted_content': None,
'query': '%23%E5%B8%B0%E3%82%8C%E3%83%9E%E3%83%B3%E3%83%87%E3%83%BC',
'tweet_volume': 12429,
'url': 'http://twitter.com/search?q=%23%E5%B8%B0%E3%82%8C%E3%83%9E%E3%83%B3%E3%83%87%E3%83%BC'}]
```

レスポンスを加工する

* days ・・・取得日(JST)
* time_Rank・・・取得時間(JST) + 何位のトレンドだったかの数値
* その他カラムは削除
```
[{'value': '#ポケモンWordle',
'days': 20220130,
'time_Rank': '1634_1'}},
{'value': '#帰れマンデー',
'days': 20220130,
'time_Rank': '1634_2'}]
```

#### 2.加工したトレンド情報をDynamoDBに格納



##### trendsData設計
| 通番  | 項目名   | 型      | PK/SK |
|-----|----------|--------|-------|
| 1   | date     | Number | PK    |
| 2   | timeRank | String | SK    |
| 3   | value    | String | -     |

-------
### postTrends.pyの処理
#### 1.DynamoDBからトレンド情報を取得
現在日付(例：202020130)でクエリし本日分のトレンドデータを取得する

集計用の辞書リストにデータを入れていく
```
[{'trend': 'dummy_trend_information', 'point': 0}]
```
ポイントはRank=1位 -> 50pt、2位 -> 49pt.......50位 -> 1ptで算出する。

同じトレンド名が存在する場合はポイントを合算する。

#### 2.トレンド情報をツイート
ポイントの降順に辞書リストをソートしレイアウトを整えてツイートする。

![a](https://user-images.githubusercontent.com/94233243/198756198-e850a249-0f50-40fc-9368-6d9228df94d6.png)

