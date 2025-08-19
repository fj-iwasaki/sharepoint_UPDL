import json # JSONファイルの読み書き
import logging # ログ出力（トークン取得失敗などの記録）
import requests # HTTPリクエスト送信（Graph APIとの通信）
import msal # Microsoft Authentication Library（MSAL）: Azure AD認証・トークン取得
import subprocess # OSコマンド実行（DNSキャッシュクリアなど）に使用
import platform # 実行環境のOS判定
import os
import sys

#########################################################
# DNSキャッシュクリア　2025/07/24　　M.I
#########################################################
def flush_dns_cache():
    system = platform.system()

    try:
        if system == "Windows":
            result = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True)
        elif system == "Darwin":  # macOS
            result = subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True, text=True)
        elif system == "Linux":
            result = subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], capture_output=True, text=True)
        else:
            print(f"❌ 未対応のOSです: {system}")
            return

        if result.returncode == 0:
            print("✅ DNSキャッシュをクリアしました。")
        else:
            print("⚠️ DNSキャッシュのクリアに失敗しました。")
            print(result.stderr)

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

#########################################################
# json読み込み、トークン取得　2025/07/24　　M.I
#########################################################
def get_access_token() -> dict:
    
    # DNSキャッシュをクリア
    flush_dns_cache()  
    
    # アクセストークンの取得
    # result = app.acquire_token_silent(config["scope"], account=None)
    result = app.acquire_token_for_client(scopes=config["scope"])

    # アクセストークンが取得できなかった場合は、AADから取得する
    if not result:
        logging.info("No suitable token exists in cache. Let's get a new one from AAD.")
        result = app.acquire_token_for_client(scopes=config["scope"])

    return result

#########################################################
# GETリクエスト送信　2025/07/24　　　M.I
#########################################################
def get_some_data_from_graph_api(endpoint: str) -> None:
    # アクセストークンの取得
    access_token = get_access_token()

    if "access_token" in access_token:
        graph_data = requests.get(
            endpoint,
            headers={'Authorization': 'Bearer ' + access_token['access_token']}, ).json()
        return graph_data
    else:
        print(access_token.get("error"))
        print(access_token.get("error_description"))
        print(access_token.get("correlation_id"))
        raise Exception("===Failed to call MS Graph API. See stderr for details.===")

#########################################################
# ファイルアップロード　2025/07/24　　M.I 
######################################################### 
def put_file_to_graph_api(endpoint: str, file_path: str) -> None:
    # アクセストークンの取得
    access_token = get_access_token()

    if "access_token" in access_token:
        with open(file_path, 'rb') as f:
            graph_data = requests.put(
                endpoint,
                headers={'Authorization': 'Bearer ' + access_token['access_token']},
                data=f).json()
        return graph_data
    else:
        print(access_token.get("error"))
        print(access_token.get("error_description"))
        print(access_token.get("correlation_id"))
        raise Exception("===Failed to call MS Graph API. See stderr for details.===")

#########################################################
# メイン処理　2025/07/24　　M.I
######################################################### 
if __name__ == "__main__":
    
    # DNSキャッシュをクリア
    flush_dns_cache() 
    
    # config.jsonの読み込み
    # config = json.load(open("parameters.json"))
    

    # 実行ファイルのあるディレクトリ（.exeと同じ場所）を取得
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(exe_dir, 'parameters.json')

    # JSONファイルの読み込み
    with open(json_path, encoding='utf-8') as f:
        config = json.load(f)

    # msal.ConfidentialClientApplicationのインスタンス化
    app = msal.ConfidentialClientApplication(
        config["client_id"], 
        authority=config["authority"],
        client_credential=config["secret"]
    )

    # サイトIDの確認
    sites = get_some_data_from_graph_api("https://graph.microsoft.com/v1.0/sites")
    target_site_name = "コミュニケーション サイト"
    target_site = None
    for site in sites["value"]:
        try:
            if site["displayName"] == target_site_name:
                target_site = site
        except KeyError:
            pass
    target_site_id = target_site["id"]
    # print(target_site_id)

    # フォルダIDの取得
    children = get_some_data_from_graph_api(f"https://graph.microsoft.com/v1.0/sites/{target_site_id}/drive/items/root/children")
    exp_dir_name = "test"
    exp_dir = [child for child in children["value"] if child["name"] == exp_dir_name][0]
    exp_dir_id = exp_dir["id"]
    # print(exp_dir_id)


    # ファイルアップロード
    filename = "hogehoge.txt"
    filepath = "./hogehoge.txt"

    resp = put_file_to_graph_api(f"https://graph.microsoft.com/v1.0/sites/{target_site_id}/drive/items/{exp_dir_id}:/{filename}:/content", filepath)
    print(resp)