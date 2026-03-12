import requests
import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class CTFdAPI:
    """
    CTFd APIクライアントクラス
    CTFdサーバーから問題情報を取得し、Markdownファイルに出力する
    """
    
    def __init__(self, base_url: str, api_token: str):
        """
        初期化メソッド
        
        Args:
            base_url: CTFdサーバーのベースURL (例: https://demo.ctfd.io)
            api_token: CTFd管理者のアクセストークン
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json'
        }
    
    def get_challenges(self) -> Optional[List[Dict]]:
        """
        全ての問題情報を取得するメソッド
        GET /api/v1/challenges エンドポイントを使用
        
        Returns:
            問題情報のリスト、エラー時はNone
        """
        url = f'{self.base_url}/api/v1/challenges'
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                return data.get('data', [])
            else:
                print(f"API返却エラー: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"リクエストエラー: {e}")
            return None
    
    def get_challenge_detail(self, challenge_id: int) -> Optional[Dict]:
        """
        特定の問題の詳細情報を取得するメソッド
        GET /api/v1/challenges/{challenge_id} エンドポイントを使用
        
        Args:
            challenge_id: 問題ID
            
        Returns:
            問題詳細情報の辞書、エラー時はNone
        """
        url = f'{self.base_url}/api/v1/challenges/{challenge_id}'
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                return data.get('data', {})
            else:
                print(f"API返却エラー (ID: {challenge_id}): {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"リクエストエラー (ID: {challenge_id}): {e}")
            return None
    
    def export_to_markdown(self, output_file: str = 'challenges.md') -> bool:
        """
        全問題情報をMarkdown形式でファイルに出力するメソッド
        問題IDの昇順でソートして出力する
        
        Args:
            output_file: 出力ファイル名
            
        Returns:
            成功時True、失敗時False
        """
        print("問題リストを取得中...")
        challenges = self.get_challenges()
        
        if challenges is None:
            print("問題リストの取得に失敗しました")
            return False
        
        # 問題IDでソート（昇順）
        challenges_sorted = sorted(challenges, key=lambda x: x.get('id', 0))
        
        print(f"{len(challenges_sorted)}個の問題が見つかりました")
        print("問題IDでソートしました")
        
        # Markdownファイルの生成
        with open(output_file, 'w', encoding='utf-8') as f:
            # ヘッダー
            f.write(f"# CTFd Challenges\n\n")
            f.write(f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"問題数: {len(challenges_sorted)}\n\n")
            f.write("---\n\n")
            
            # 各問題の詳細を取得して出力
            for idx, challenge in enumerate(challenges_sorted, 1):
                challenge_id = challenge.get('id')
                challenge_name = challenge.get('name', 'Unknown')
                
                print(f"[{idx}/{len(challenges_sorted)}] 問題ID {challenge_id}: {challenge_name} の詳細を取得中...")
                
                # 詳細情報を取得
                detail = self.get_challenge_detail(challenge_id)
                
                if detail:
                    # 問題タイトル
                    f.write(f"## {detail.get('name', 'Unknown')}\n\n")
                    
                    # 基本情報テーブル
                    f.write("### 基本情報\n\n")
                    f.write(f"- **問題ID**: {detail.get('id', 'N/A')}\n")
                    f.write(f"- **カテゴリ**: {detail.get('category', 'N/A')}\n")
                    f.write(f"- **配点**: {detail.get('value', 'N/A')}\n")
                    f.write(f"- **タイプ**: {detail.get('type', 'N/A')}\n")
                    f.write(f"- **状態**: {detail.get('state', 'N/A')}\n")
                    f.write(f"- **解答数**: {detail.get('solves', 0)}\n")
                    
                    # 最大試行回数がある場合
                    if detail.get('max_attempts'):
                        f.write(f"- **最大試行回数**: {detail.get('max_attempts')}\n")
                    
                    # 自分が解いたかどうか
                    if detail.get('solved_by_me'):
                        f.write(f"- **自分の解答**: ✅ 解答済み\n")
                    else:
                        f.write(f"- **自分の解答**: ❌ 未解答\n")
                    
                    f.write("\n")
                    
                    # 問題文
                    f.write("### 問題文\n\n")
                    description = detail.get('description', '')
                    if description:
                        f.write(f"{description}\n\n")
                    else:
                        f.write("*問題文なし*\n\n")
                    
                    # 接続情報がある場合
                    if detail.get('connection_info'):
                        f.write("### 接続情報\n\n")
                        f.write(f"```\n{detail.get('connection_info')}\n```\n\n")
                    
                    # 作成者情報がある場合
                    if detail.get('attribution'):
                        f.write(f"**作成者**: {detail.get('attribution')}\n\n")
                    
                    f.write("---\n\n")
                else:
                    # 詳細取得失敗時は基本情報のみ出力
                    f.write(f"## {challenge_name}\n\n")
                    f.write(f"- **問題ID**: {challenge_id}\n")
                    f.write(f"- **カテゴリ**: {challenge.get('category', 'N/A')}\n")
                    f.write(f"- **配点**: {challenge.get('value', 'N/A')}\n")
                    f.write("\n*詳細情報の取得に失敗しました*\n\n")
                    f.write("---\n\n")
        
        print(f"\n✅ Markdownファイルを出力しました: {output_file}")
        return True



def main():
    """
    メイン実行関数
    使用例を示す
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 環境変数から設定を読み込む
    CTFD_URL = os.getenv("CTFD_URL", "https://demo.ctfd.io")
    API_TOKEN = os.getenv("CTFD_TOKEN", "")
    OUTPUT_FILE = "ctfd_challenges.md"
    
    if not API_TOKEN:
        print("Error: CTFD_TOKEN not set in environment")
        print("Please set CTFD_URL and CTFD_TOKEN in .env file")
        return
    
    # CTFd APIクライアントを初期化
    client = CTFdAPI(CTFD_URL, API_TOKEN)
    
    # Markdownファイルに出力
    client.export_to_markdown(OUTPUT_FILE)



if __name__ == "__main__":
    main()
