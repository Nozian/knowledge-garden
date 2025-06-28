from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import json
import re
from datetime import datetime
import os

knowledge_bp = Blueprint('knowledge', __name__)

# グローバル変数でデータを保存（本番環境ではデータベースを使用）
conversations_data = []
search_history = []

@knowledge_bp.route('/upload', methods=['POST'])
@cross_origin()
def upload_file():
    """ファイルアップロードとチャットログ解析"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        # ファイル内容を読み取り
        content = file.read().decode('utf-8')
        
        # ChatGPTログを解析
        parsed_data = parse_chatgpt_log(content)
        
        # グローバル変数に保存
        global conversations_data
        conversations_data = parsed_data
        
        # 統計情報を計算
        total_messages = len(parsed_data)
        total_conversations = len(set(msg['conversationId'] for msg in parsed_data))
        
        return jsonify({
            'success': True,
            'message': f'{total_messages}個のメッセージが正常に処理されました',
            'data': {
                'total_messages': total_messages,
                'total_conversations': total_conversations,
                'messages': parsed_data
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'ファイル処理エラー: {str(e)}'}), 500

@knowledge_bp.route('/search', methods=['POST'])
@cross_origin()
def search_messages():
    """メッセージ検索"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        date_filter = data.get('date_filter', 'all')
        speaker_filter = data.get('speaker_filter', 'all')
        
        if not query:
            return jsonify({'error': '検索キーワードを入力してください'}), 400
        
        # 検索履歴に追加
        global search_history
        search_history.append({
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'filters': {
                'date_filter': date_filter,
                'speaker_filter': speaker_filter
            }
        })
        
        # 検索実行
        results = perform_search(query, date_filter, speaker_filter)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'total_results': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': f'検索エラー: {str(e)}'}), 500

@knowledge_bp.route('/recent-chats', methods=['GET'])
@cross_origin()
def get_recent_chats():
    """最近のチャット概要を取得"""
    try:
        summaries = extract_chat_summaries(conversations_data)
        return jsonify({
            'success': True,
            'summaries': summaries
        })
    except Exception as e:
        return jsonify({'error': f'チャット概要取得エラー: {str(e)}'}), 500

@knowledge_bp.route('/stats', methods=['GET'])
@cross_origin()
def get_stats():
    """統計情報を取得"""
    try:
        total_messages = len(conversations_data)
        total_conversations = len(set(msg['conversationId'] for msg in conversations_data)) if conversations_data else 0
        total_searches = len(search_history)
        
        return jsonify({
            'success': True,
            'stats': {
                'messages': total_messages,
                'conversations': total_conversations,
                'searches': total_searches
            }
        })
    except Exception as e:
        return jsonify({'error': f'統計情報取得エラー: {str(e)}'}), 500

def parse_chatgpt_log(content):
    """ChatGPTログを解析する"""
    try:
        # JSONファイルの場合
        data = json.loads(content)
        normalized_messages = []
        
        for conversation in data:
            conversation_id = conversation.get('id', 'unknown')
            title = conversation.get('title', 'Untitled Conversation')
            
            if 'mapping' in conversation:
                # ChatGPT形式
                for node_id, node in conversation['mapping'].items():
                    message = node.get('message')
                    if message and message.get('content') and message['content'].get('parts'):
                        content_parts = message['content']['parts']
                        if content_parts and content_parts[0]:
                            normalized_messages.append({
                                'conversationId': conversation_id,
                                'conversationTitle': title,
                                'speaker': 'user' if message.get('author', {}).get('role') == 'user' else 'assistant',
                                'content': content_parts[0],
                                'timestamp': message.get('create_time', 0)
                            })
        
        return normalized_messages
        
    except json.JSONDecodeError:
        # テキストファイルの場合の簡単な解析
        lines = content.split('\n')
        messages = []
        current_conversation = 'text_conversation'
        
        for i, line in enumerate(lines):
            if line.strip():
                messages.append({
                    'conversationId': current_conversation,
                    'conversationTitle': 'Text Conversation',
                    'speaker': 'user' if i % 2 == 0 else 'assistant',
                    'content': line.strip(),
                    'timestamp': datetime.now().timestamp()
                })
        
        return messages

def perform_search(query, date_filter='all', speaker_filter='all'):
    """検索を実行する"""
    if not conversations_data:
        return []
    
    results = []
    query_lower = query.lower()
    
    for message in conversations_data:
        # テキスト検索
        if query_lower in message['content'].lower():
            # フィルター適用
            if speaker_filter != 'all' and message['speaker'] != speaker_filter:
                continue
            
            # 日付フィルター（簡単な実装）
            if date_filter != 'all':
                # 実際の実装では日付を適切に処理
                pass
            
            # ハイライト処理
            highlighted_content = highlight_search_terms(message['content'], query)
            
            result = message.copy()
            result['highlighted_content'] = highlighted_content
            results.append(result)
    
    return results

def highlight_search_terms(text, query):
    """検索語をハイライトする"""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(f'<mark>{query}</mark>', text)

def extract_chat_summaries(conversations):
    """チャット概要を抽出する"""
    if not conversations:
        return []
    
    # 会話IDごとにグループ化
    conversation_groups = {}
    for msg in conversations:
        conv_id = msg['conversationId']
        if conv_id not in conversation_groups:
            conversation_groups[conv_id] = []
        conversation_groups[conv_id].append(msg)
    
    summaries = []
    for conv_id, messages in conversation_groups.items():
        # タイムスタンプでソート
        messages.sort(key=lambda x: x.get('timestamp', 0))
        
        # 最初のユーザーメッセージとアシスタントメッセージを取得
        user_message = None
        assistant_message = None
        
        for msg in messages:
            if msg['speaker'] == 'user' and not user_message:
                user_message = msg
            elif msg['speaker'] == 'assistant' and not assistant_message:
                assistant_message = msg
            
            if user_message and assistant_message:
                break
        
        if user_message or assistant_message:
            summary = {
                'conversationId': conv_id,
                'title': messages[0].get('conversationTitle', 'Untitled'),
                'userMessage': user_message['content'][:100] + '...' if user_message else '',
                'assistantMessage': assistant_message['content'][:100] + '...' if assistant_message else '',
                'timestamp': max(msg.get('timestamp', 0) for msg in messages),
                'messageCount': len(messages)
            }
            summaries.append(summary)
    
    # 最新順でソート
    summaries.sort(key=lambda x: x['timestamp'], reverse=True)
    return summaries

