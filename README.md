# trends
### 1.TwitterAPIからトレンド情報を取得
 URL = https://api.twitter.com/1.1/trends/place.json?id=23424856

id = 23424856 とすることで日本のトレンド情報を取得できる
不要なカラムは削除する

### 2.加工したトレンド情報をDynamoDBに格納
カラムは取得日付(Number)、時刻+順位(String)、トレンド情報(String)