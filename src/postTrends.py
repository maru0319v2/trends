import json
import pprint
import datetime
import locale
import twitter
from boto3.dynamodb.conditions import Key
from boto3.session import Session
from requests_oauthlib import OAuth1Session

import config

auth = twitter.OAuth(
    consumer_key=config.CK,
    consumer_secret=config.CKS,
    token=config.AT,
    token_secret=config.ATS
)
t = twitter.Twitter(auth=auth)


def main():
    # 読み込むDynamoDBの情報を取得
    table = get_table()
    # DBから条件に合致するトレンド情報取得
    dicts = get_trends(table)

    # 取得結果を集計する
    totalled_dicts = totalling_dicts(dicts)

    # POST用文字列生成しツイートする(1位～5位)
    post_str = generate_post_str(dicts[0]['date'], totalled_dicts, 0)
    tweet(post_str, None)

    # POST用文字列生成しツイートする(6位～10位)
    post_str = generate_post_str(dicts[0]['date'], totalled_dicts, 1)
    tweet(post_str, get_latest_id()['id'])


# 読み込むDynamoDBの情報を取得
def get_table():
    session = Session(
        aws_access_key_id=config.AAK,
        aws_secret_access_key=config.AAS,
        region_name=config.REGION_NAME
    )
    dynamodb = session.resource('dynamodb')
    dynamo_table = dynamodb.Table('trendsData')
    return dynamo_table


# DBから条件に合致するトレンド情報取得
def get_trends(table):
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9), 'JST'))
    date = int(now.strftime("%Y%m%d"))

    # 今日の日付(例.20220130)でクエリ
    response = table.query(
        KeyConditionExpression=Key('date').eq(date))

    # 取得結果の表示
    dicts = response['Items']
    print('Queried items: %d' % len(dicts))

    return dicts


# 取得結果を集計する  1位=50pt,2位=49pt・・・50位=1pt
def totalling_dicts(origin_dicts):
    # 集計用辞書
    totalled_dicts = [{'trend': 'dummy_trend_information', 'point': 0}]

    # トレンド情報のループ
    for origin_dict in origin_dicts:
        # 重複判定フラグ
        duplicate_flg = False
        # _で文字列を区切り_から後部分だけ取り出してポイントを付ける (例.'0059_1' -> 50)
        split_str = origin_dict['timeRank'].split('_')
        rank = split_str[1]
        point = 51 - int(rank)
        trend = origin_dict['value']

        # 集計用辞書のループ
        for t_dict in totalled_dicts:
            # 集計用辞書に既に存在するか判定
            if t_dict['trend'] == trend:
                duplicate_flg = True
                break
            else:
                duplicate_flg = False

        if duplicate_flg is True:
            # 重複している場合はポイントを加算する
            t_dict['point'] = int(t_dict['point']) + int(point)
        else:
            # 重複していない場合は集計用辞書に追記する
            totalled_dicts.append({'trend': trend, 'point': point})

    # 集計結果をポイントの降順でソートする
    totalled_dicts = sorted(totalled_dicts, key=lambda x: x['point'], reverse=True)
    # 集計結果表示
    print('Totalled items: %d' % len(totalled_dicts))
    return totalled_dicts


# POST用文字列生成
def generate_post_str(date, totalled_dicts, flg):
    year = int(str(date)[:4])
    month = int(str(date)[4:6])
    day = int(str(date)[6:8])
    # 曜日を判定する
    locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
    date = datetime.date(year, month, day)
    week = date.strftime('%a')

    post_str = str(year) + "年" + str(month) + "月" + str(day) + "日(" + week + ")トレンド日別集計" + str(1 if flg == 0 else 2) + "/2\n"
    for i in range(5):
        end_str = "\n" if i != 4 else ""
        line = str(i + 1 if flg == 0 else i + 6) + "位(" + str(
            totalled_dicts[i if flg == 0 else i + 6]['point']) + "p) " \
                    + str(totalled_dicts[i if flg == 0 else i + 6]['trend']) + end_str
        post_str += line

    # 140文字オーバーしている場合、最後の行を削除
    if len(post_str) > 140:
        post_str = post_str.rstrip("\n"+line)

    pprint.pprint(post_str)
    return post_str


# ツイートする
def tweet(post_str, latest_id):
    t.statuses.update(status=post_str, in_reply_to_status_id=latest_id)
    print('Successfully posted trends. length = ' + str(len(post_str)))


# 最新ツイートIDを取得
def get_latest_id():
    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    params = {
        "count": 1,
        "exclude_replies": True,
        "include_rts": False
    }
    latest_tweet_auth = OAuth1Session(config.CK, config.CKS, config.AT, config.ATS)
    req = latest_tweet_auth.get(url, params=params)

    if req.status_code == 200:
        latest_tweet = json.loads(req.text)[0]
        return latest_tweet
    else:
        return req.status_code


if __name__ == '__main__':
    main()
