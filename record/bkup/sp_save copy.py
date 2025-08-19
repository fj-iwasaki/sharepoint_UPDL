import json # JSONファイルの読み書き
import logging # ログ出力（トークン取得失敗などの記録）
import requests # HTTPリクエスト送信（Graph APIとの通信）
import msal # Microsoft Authentication Library（MSAL）: Azure AD認証・トークン取得
import subprocess # OSコマンド実行（DNSキャッシュクリアなど）に使用
import platform # 実行環境のOS判定
import os
import sys

#########################################################
# ログ出力設定　2025/07/24　　M.I
#########################################################
exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(exe_dir, 'app.log')
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#########################################################
# DNSキャッシュクリア　2025/07/24　　M.I
#########################################################
def flush_dns_cache():
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True)
        elif system == "Darwin":
            result = subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True, text=True)
        elif system == "Linux":
            result = subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], capture_output=True, text=True)
        else:
            logging.error(f"未対応のOS: {system}")
            return

        if result.returncode == 0:
            logging.info("DNSキャッシュをクリアしました。")
        else:
            logging.warning(f"DNSキャッシュのクリアに失敗: {result.stderr}")
    except Exception as e:
        logging.exception(f"DNSキャッシュクリア中にエラー発生: {e}")

#########################################################
# アクセストークン取得　2025/07/24　　M.I
#########################################################
def get_access_token() -> dict:
    try:
        # DNSキャッシュをクリア
        flush_dns_cache()
        # アクセストークンの取得
        result = app.acquire_token_for_client(scopes=config["scope"])
        # アクセストークンが取得できなかった場合は、AADから取得する
        if not result:
            logging.info("キャッシュにトークンなし。AADから新規取得。")
            result = app.acquire_token_for_client(scopes=config["scope"])
        return result
    except Exception as e:
        logging.exception(f"アクセストークン取得失敗: {e}")
        return {}

#########################################################
# Graph APIからデータ取得　2025/07/24　　M.I
#########################################################
def get_some_data_from_graph_api(endpoint: str) -> dict:
    try:
        # アクセストークンの取得
        access_token = get_access_token()
        if "access_token" in access_token:
            response = requests.get(endpoint, headers={'Authorization': 'Bearer ' + access_token['access_token']})
            response.raise_for_status()
            return response.json()
        else:
            logging.error(f"トークン取得失敗: {access_token}")
            raise Exception("MS Graph API呼び出し失敗")
    except Exception as e:
        logging.exception(f"Graph APIデータ取得失敗: {e}")
        return {}

#########################################################
# ファイルアップロード　2025/07/24　　M.I
#########################################################
def put_file_to_graph_api(endpoint: str, file_path: str) -> dict:
    try:
        # アクセストークンの取得
        access_token = get_access_token()
        if "access_token" in access_token:
            with open(file_path, 'rb') as f:
                response = requests.put(endpoint, headers={'Authorization': 'Bearer ' + access_token['access_token']}, data=f)
                response.raise_for_status()
                return response.json()
        else:
            logging.error(f"トークン取得失敗: {access_token}")
            raise Exception("MS Graph APIファイルアップロード失敗")
    except Exception as e:
        logging.exception(f"ファイルアップロード失敗: {e}")
        return {}

#########################################################
# メイン処理　2025/07/24　　M.I
#########################################################
if __name__ == "__main__":
    try:

        # DNSキャッシュをクリア
        flush_dns_cache()

        # 実行ファイルのあるディレクトリ（.exeと同じ場所）を取得
        json_path = os.path.join(exe_dir, 'parameters.json')

        # JSONファイルの読み込み
        with open(json_path, encoding='utf-8') as f:
            config = json.load(f)

        app = msal.ConfidentialClientApplication(
            config["client_id"],
            authority=config["authority"],
            client_credential=config["secret"]
        )

        # サイトIDの取得
        target_site_name = config["target_site_name"]
        sites = get_some_data_from_graph_api("https://graph.microsoft.com/v1.0/sites")
        target_site = next((site for site in sites.get("value", []) if site.get("displayName") == target_site_name), None)
        if not target_site:
            raise Exception(f"サイト名 '{target_site_name}' が見つかりません。")
        target_site_id = target_site["id"]

        # フォルダIDの取得
        exp_dir_name = config["exp_dir_name"]
        children = get_some_data_from_graph_api(f"https://graph.microsoft.com/v1.0/sites/{target_site_id}/drive/items/root/children")
        exp_dir = next((child for child in children.get("value", []) if child.get("name") == exp_dir_name), None)
        if not exp_dir:
            raise Exception(f"フォルダ名 '{exp_dir_name}' が見つかりません。")
        exp_dir_id = exp_dir["id"]

        # 引数からファイルパスを取得（なければJSONから）
        if len(sys.argv) > 1:
            filepath = sys.argv[1]
            logging.info(f"引数からファイルパスを取得: {filepath}")
        else:
            filepath = config["filename"]
            logging.info(f"JSONからファイルパスを取得: {filepath}")
        filename = os.path.basename(filepath)

        resp = put_file_to_graph_api(
            f"https://graph.microsoft.com/v1.0/sites/{target_site_id}/drive/items/{exp_dir_id}:/{filename}:/content",
            filepath
        )
        print(resp)
    except Exception as e:
        logging.exception(f"メイン処理中にエラー発生: {e}")