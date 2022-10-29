import json
import pprint
import datetime
import locale
import boto3
import twitter
import unicodedata
from boto3.dynamodb.conditions import Key
from boto3.session import Session
from requests_oauthlib import OAuth1Session
from botocore.exceptions import ClientError


session = boto3.session.Session()
client = session.client(
    service_name='secretsmanager',
    region_name="ap-northeast-1"
)
try:
    get_secret_value_response = client.get_secret_value(
        SecretId="dev/twiTrend"
    )
except ClientError as e:
    raise e
secret = json.loads(get_secret_value_response['SecretString'])
TW_CONSUMER_KEY = secret['TW_CONSUMER_KEY']
TW_CONSUMER_KEY_SECRET = secret['TW_CONSUMER_KEY_SECRET']
TW_ACCESS_TOKEN = secret['TW_ACCESS_TOKEN']
TW_ACCESS_TOKEN_SECRET = secret['TW_ACCESS_TOKEN_SECRET']
AWS_ACCESS_KEY = secret['AWS_ACCESS_KEY']
AWS_ACCESS_SECRET = secret['AWS_ACCESS_SECRET']


def lambda_handler(event, lambda_context):
    # 読み込むDynamoDBの情報を取得
    table = get_table()
    # DBから条件に合致するトレンド情報取得
    dicts = get_trends(table)

    # 取得結果を集計する
    totalled_dicts = totalling_dicts(dicts)

    # POST用文字列生成しツイートする
    post_str = generate_post_str(dicts[0]['date'], totalled_dicts)
    tweet(post_str, None)


# 読み込むDynamoDBの情報を取得
def get_table():
    session = Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_ACCESS_SECRET,
        region_name="ap-northeast-1"
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
def generate_post_str(date, totalled_dicts):
    year = int(str(date)[:4])
    month = int(str(date)[4:6])
    day = int(str(date)[6:8])
    # 曜日を判定する
    locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
    date = datetime.date(year, month, day)
    week = date.strftime('%a')

    post_str = str(year) + "年" + str(month) + "月" + str(day) + "日(" + week + ")上位トレンド集計" + "\n"
    i = 0
    # 全角は2、半角は1として合計280まで投稿できる。
    while count_text(post_str) < 280:
        line = str(i + 1) + "位(" + str(totalled_dicts[i]['point']) + "p) " + str(totalled_dicts[i]['trend']) + "\n"
        post_str += line
        i += 1
    post_str = post_str.rstrip("\n" + line)

    pprint.pprint(post_str)
    return post_str


# 文字数判定
def count_text(message):
    text_length = 0
    for i in message:
        letter = unicodedata.east_asian_width(i)
        if letter == 'H':  # 半角
            text_length = text_length + 1
        elif letter == 'Na':  # 半角
            text_length = text_length + 1
        elif letter == 'F':  # 全角
            text_length = text_length + 2
        elif letter == 'A':  # 全角
            text_length = text_length + 2
        elif letter == 'W':  # 全角
            text_length = text_length + 2
        else:  # 半角
            text_length = text_length + 1
    return text_length


# ツイートする
def tweet(post_str, latest_id):
    auth = twitter.OAuth(
        consumer_key=TW_CONSUMER_KEY,
        consumer_secret=TW_CONSUMER_KEY_SECRET,
        token=TW_ACCESS_TOKEN,
        token_secret=TW_ACCESS_TOKEN_SECRET
    )
    t = twitter.Twitter(auth=auth)
    t.statuses.update(status=post_str, in_reply_to_status_id=latest_id)
    print('Successfully posted trends. length = ' + str(len(post_str)))
