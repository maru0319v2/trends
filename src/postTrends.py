import pprint
import datetime

import twitter
from boto3.dynamodb.conditions import Key
from boto3.session import Session
import config


def main():
    # 読み込むDynamoDBの情報を取得
    table = get_dynamo_table()
    # DBから条件に合致するトレンド情報取得
    dicts = get_trends(table)

    # 取得結果を集計する
    totalled_dicts = totalling_dicts(dicts)
    # 集計結果をポイントの降順でソートする
    totalled_dicts = sorted(totalled_dicts, key=lambda x: x['point'], reverse=True)

    # 集計結果表示
    print('Totalled items: %d' % len(totalled_dicts))

    # POST用文字列生成
    post_str = str(dicts[0]['date'])
    post_str = str(post_str[4:6]) + "/" + str(post_str[6:8]) + "トレンド集計結果\n" + \
               "1位 (" + str(totalled_dicts[0]['point']) + "pt) " + str(totalled_dicts[0]['trend']) + "\n" + \
               "2位 (" + str(totalled_dicts[1]['point']) + "pt) " + str(totalled_dicts[1]['trend']) + "\n" + \
               "3位 (" + str(totalled_dicts[2]['point']) + "pt) " + str(totalled_dicts[2]['trend']) + "\n" + \
               "4位 (" + str(totalled_dicts[3]['point']) + "pt) " + str(totalled_dicts[3]['trend']) + "\n" + \
               "5位 (" + str(totalled_dicts[4]['point']) + "pt) " + str(totalled_dicts[4]['trend'])

    pprint.pprint(post_str)

    # トレンド情報をツイートする
    tweet(post_str)


# 取得結果を集計する  1位=50pt,2位=49pt・・・50位=1pt
def totalling_dicts(origin_dicts):
    # 集計用辞書
    totalled_dicts = [{'trend': 'dummy_trend_information', 'point': 0}]

    # トレンド情報のループ
    for origin_dict in origin_dicts:
        # 重複判定フラグ
        duplicate_flg = False
        # _で文字列を区切り_から後部分だけ取り出してポイントを付ける (例.'0059_1' -> 50)
        splited_str = origin_dict['timeRank'].split('_')
        rank = splited_str[1]
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

    return totalled_dicts


# DBから条件に合致するトレンド情報取得
def get_trends(table):
    t_delta = datetime.timedelta(hours=9)
    jst = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(jst)
    date = int(now.strftime("%Y%m%d"))

    # 今日の日付(例.20220130)でクエリ
    response = table.query(
        KeyConditionExpression=Key('date').eq(date))

    # 取得結果の表示
    dicts = response['Items']
    print('Queried items: %d' % len(dicts))

    return dicts


# 読み込むDynamoDBの情報を取得
def get_dynamo_table():
    session = Session(
        aws_access_key_id=config.AAK,
        aws_secret_access_key=config.AAS,
        region_name=config.REGION_NAME
    )
    dynamodb = session.resource('dynamodb')
    dynamo_table = dynamodb.Table('trendsData')
    return dynamo_table


# トレンド情報をツイートする
def tweet(text):
    auth = twitter.OAuth(
        consumer_key=config.CK,
        consumer_secret=config.CKS,
        token=config.AT,
        token_secret=config.ATS
    )

    t = twitter.Twitter(auth=auth)
    status = text
    t.statuses.update(status=status)
    print('Successfully posted trends.')


if __name__ == '__main__':
    main()
