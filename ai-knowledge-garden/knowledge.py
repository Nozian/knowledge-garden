from flask import Blueprint, request, jsonify
import json
import re
from datetime import datetime
import os
import tempfile

knowledge_bp = Blueprint('knowledge', __name__)

# グローバル変数でデータを保存（本番環境では適切なデータベースを使用）
chat_data = {
    'messages': [],
    'conversations': [],
    'stats': {'messages': 0, 'conversations': 0, 'searches': 0}
}

def detect_service_type(data):
    """ファイルの内容からAIサービスの種類を判定"""
    try:
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            
            # ChatGPT形式の判定
            if isinstance(first_item, dict):
                if 'mapping' in first_item and 'conversation_id' in first_item:
                    return 'chatgpt'
                elif 'title' in first_item and 'create_time' in first_item:
                    return 'chatgpt'
                elif 'role' in first_item and 'content' in first_item:
                    return 'openai_api'
        
        # テキスト形式の場合
        if isinstance(data, str):
            # Claude形式の判定
            if 'Human:' in data and 'Assistant:' in data:
                return 'claude_text'
            # Gemini形式の判定
            elif 'User:' in data and 'Gemini:' in data:
                return 'gemini_text'
            # Grok形式の判定
            elif 'You:' in data and 'Grok:' in data:
                return 'grok_text'
            # 一般的なチャット形式
            elif any(keyword in data.lower() for keyword in ['user:', 'assistant:', 'ai:', 'bot:']):
                return 'generic_chat'
        
        return 'unknown'
    except Exception as e:
        print(f"サービス判定エラー: {e}")
        return 'unknown'

def parse_chatgpt_data(data):
    """ChatGPTのエクスポートデータを解析"""
    messages = []
    conversations = []
    
    try:
        for conversation in data:
            if not isinstance(conversation, dict):
                continue
                
            conv_id = conversation.get('id', f"conv_{len(conversations)}")
            title = conversation.get('title', 'Untitled Conversation')
            create_time = conversation.get('create_time', datetime.now().timestamp())
            
            # mappingからメッセージを抽出
            mapping = conversation.get('mapping', {})
            conv_messages = []
            
            for node_id, node in mapping.items():
                message = node.get('message')
                if not message or not message.get('content'):
                    continue
                    
                content_parts = message.get('content', {}).get('parts', [])
                if not content_parts:
                    continue
                    
                role = message.get('author', {}).get('role', 'unknown')
                content = ' '.join(content_parts) if isinstance(content_parts, list) else str(content_parts)
                
                if content.strip():
                    msg = {
                        'role': 'user' if role == 'user' else 'assistant',
                        'content': content,
                        'timestamp': message.get('create_time', create_time),
                        'conversation_id': conv_id,
                        'conversation_title': title,
                        'service': 'ChatGPT'
                    }
                    messages.append(msg)
                    conv_messages.append(msg)
            
            if conv_messages:
                conversations.append({
                    'id': conv_id,
                    'title': title,
                    'create_time': create_time,
                    'message_count': len(conv_messages),
                    'service': 'ChatGPT'
                })
    except Exception as e:
        print(f"ChatGPT解析エラー: {e}")
    
    return messages, conversations

def parse_text_format(text_data, service_name, user_prefix, assistant_prefix):
    """テキスト形式のデータを解析（汎用）"""
    messages = []
    conversations = []
    
    try:
        # 改行で分割してメッセージを抽出
        lines = text_data.split('\n')
        current_role = None
        current_content = []
        
        conv_id = f"{service_name.lower()}_conv_{datetime.now().timestamp()}"
        title = f"{service_name} Conversation"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(user_prefix):
                # 前のメッセージを保存
                if current_role and current_content:
                    content = ' '.join(current_content).strip()
                    if content:
                        msg = {
                            'role': current_role,
                            'content': content,
                            'timestamp': datetime.now().timestamp() + len(messages),
                            'conversation_id': conv_id,
                            'conversation_title': title,
                            'service': service_name
                        }
                        messages.append(msg)
                
                # 新しいユーザーメッセージ開始
                current_role = 'user'
                current_content = [line[len(user_prefix):].strip()]
                
            elif line.startswith(assistant_prefix):
                # 前のメッセージを保存
                if current_role and current_content:
                    content = ' '.join(current_content).strip()
                    if content:
                        msg = {
                            'role': current_role,
                            'content': content,
                            'timestamp': datetime.now().timestamp() + len(messages),
                            'conversation_id': conv_id,
                            'conversation_title': title,
                            'service': service_name
                        }
                        messages.append(msg)
                
                # 新しいアシスタントメッセージ開始
                current_role = 'assistant'
                current_content = [line[len(assistant_prefix):].strip()]
                
            else:
                # 継続行
                if current_role:
                    current_content.append(line)
        
        # 最後のメッセージを保存
        if current_role and current_content:
            content = ' '.join(current_content).strip()
            if content:
                msg = {
                    'role': current_role,
                    'content': content,
                    'timestamp': datetime.now().timestamp() + len(messages),
                    'conversation_id': conv_id,
                    'conversation_title': title,
                    'service': service_name
                }
                messages.append(msg)
        
        if messages:
            conversations.append({
                'id': conv_id,
                'title': title,
                'create_time': datetime.now().timestamp(),
                'message_count': len(messages),
                'service': service_name
            })
    except Exception as e:
        print(f"{service_name}解析エラー: {e}")
    
    return messages, conversations

def parse_openai_api_format(data):
    """OpenAI API形式のデータを解析"""
    messages = []
    conversations = []
    
    try:
        conv_id = f"api_conv_{datetime.now().timestamp()}"
        title = "API Conversation"
        
        for i, msg in enumerate(data):
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                message = {
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': datetime.now().timestamp() + i,
                    'conversation_id': conv_id,
                    'conversation_title': title,
                    'service': 'OpenAI API'
                }
                messages.append(message)
        
        if messages:
            conversations.append({
                'id': conv_id,
                'title': title,
                'create_time': datetime.now().timestamp(),
                'message_count': len(messages),
                'service': 'OpenAI API'
            })
    except Exception as e:
        print(f"OpenAI API解析エラー: {e}")
    
    return messages, conversations

@knowledge_bp.route('/upload', methods=['POST'])
def upload_file():
    """複数のAIサービスのログファイルをアップロード"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        # ファイル内容を読み取り
        try:
            file_content = file.read()
            print(f"ファイルサイズ: {len(file_content)} bytes")
        except Exception as e:
            return jsonify({'error': f'ファイル読み取りエラー: {str(e)}'}), 400
        
        # データの解析を試行
        data = None
        try:
            # JSONとして解析を試行
            data = json.loads(file_content.decode('utf-8'))
            print("JSONファイルとして解析成功")
        except (json.JSONDecodeError, UnicodeDecodeError):
            # テキストファイルとして処理
            try:
                data = file_content.decode('utf-8')
                print("テキストファイルとして解析成功")
            except UnicodeDecodeError:
                try:
                    data = file_content.decode('utf-8', errors='ignore')
                    print("テキストファイルとして解析成功（エラー無視）")
                except Exception as e:
                    return jsonify({'error': f'ファイルの文字エンコーディングが不正です: {str(e)}'}), 400
        
        if data is None:
            return jsonify({'error': 'ファイルの内容を読み取れませんでした'}), 400
        
        # サービスタイプを判定
        service_type = detect_service_type(data)
        print(f"検出されたサービスタイプ: {service_type}")
        
        # サービスタイプに応じて解析
        messages = []
        conversations = []
        
        if service_type == 'chatgpt':
            messages, conversations = parse_chatgpt_data(data)
        elif service_type == 'claude_text':
            messages, conversations = parse_text_format(data, 'Claude', 'Human:', 'Assistant:')
        elif service_type == 'gemini_text':
            messages, conversations = parse_text_format(data, 'Gemini', 'User:', 'Gemini:')
        elif service_type == 'grok_text':
            messages, conversations = parse_text_format(data, 'Grok', 'You:', 'Grok:')
        elif service_type == 'openai_api':
            messages, conversations = parse_openai_api_format(data)
        elif service_type == 'generic_chat':
            # 汎用チャット形式として処理
            messages, conversations = parse_text_format(data, 'Generic Chat', 'User:', 'Assistant:')
        else:
            # 不明な形式でも基本的な処理を試行
            if isinstance(data, str) and len(data.strip()) > 0:
                messages, conversations = parse_text_format(data, 'Unknown Service', 'User:', 'Assistant:')
            else:
                return jsonify({'error': f'サポートされていないファイル形式です。検出されたタイプ: {service_type}'}), 400
        
        if not messages:
            return jsonify({'error': 'ファイルからメッセージを抽出できませんでした。ファイル形式を確認してください。'}), 400
        
        # データを統合
        chat_data['messages'].extend(messages)
        chat_data['conversations'].extend(conversations)
        
        # 統計を更新
        chat_data['stats']['messages'] = len(chat_data['messages'])
        chat_data['stats']['conversations'] = len(chat_data['conversations'])
        
        print(f"処理完了: {len(messages)}メッセージ, {len(conversations)}会話")
        
        return jsonify({
            'success': True,
            'message': f'{len(messages)}個のメッセージが正常に処理されました',
            'service_type': service_type,
            'stats': chat_data['stats']
        })
        
    except Exception as e:
        print(f"アップロードエラー: {str(e)}")
        return jsonify({'error': f'ファイル処理中にエラーが発生しました: {str(e)}'}), 500

@knowledge_bp.route('/search', methods=['POST'])
def search_messages():
    """統合されたメッセージを検索"""
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        date_filter = data.get('date_filter', 'all')
        speaker_filter = data.get('speaker_filter', 'all')
        service_filter = data.get('service_filter', 'all')
        
        if not query:
            return jsonify({'results': [], 'total': 0})
        
        # 検索実行
        results = []
        for message in chat_data['messages']:
            # テキスト検索
            if query not in message['content'].lower():
                continue
            
            # 話者フィルター
            if speaker_filter != 'all' and message['role'] != speaker_filter:
                continue
            
            # サービスフィルター
            if service_filter != 'all' and message['service'] != service_filter:
                continue
            
            # ハイライト処理
            highlighted_content = re.sub(
                f'({re.escape(query)})',
                r'<mark>\1</mark>',
                message['content'],
                flags=re.IGNORECASE
            )
            
            result = message.copy()
            result['highlighted_content'] = highlighted_content
            results.append(result)
        
        # 検索回数を更新
        chat_data['stats']['searches'] += 1
        
        return jsonify({
            'results': results,
            'total': len(results),
            'query': query,
            'stats': chat_data['stats']
        })
        
    except Exception as e:
        print(f"検索エラー: {str(e)}")
        return jsonify({'error': f'検索中にエラーが発生しました: {str(e)}'}), 500

@knowledge_bp.route('/recent-chats', methods=['GET'])
def get_recent_chats():
    """最近のチャット概要を取得（サービス別）"""
    try:
        # 会話を作成時間順にソート
        sorted_conversations = sorted(
            chat_data['conversations'],
            key=lambda x: x['create_time'],
            reverse=True
        )
        
        # 各会話の最初のメッセージを取得
        summaries = []
        for conv in sorted_conversations[:10]:  # 最新10件
            conv_messages = [
                msg for msg in chat_data['messages']
                if msg['conversation_id'] == conv['id']
            ]
            
            if conv_messages:
                # 最初のユーザーメッセージとアシスタントメッセージを取得
                user_msg = next((msg for msg in conv_messages if msg['role'] == 'user'), None)
                assistant_msg = next((msg for msg in conv_messages if msg['role'] == 'assistant'), None)
                
                summary = {
                    'conversation_id': conv['id'],
                    'title': conv['title'],
                    'service': conv['service'],
                    'create_time': conv['create_time'],
                    'message_count': conv['message_count'],
                    'user_message': user_msg['content'][:200] + '...' if user_msg and len(user_msg['content']) > 200 else user_msg['content'] if user_msg else '',
                    'assistant_message': assistant_msg['content'][:200] + '...' if assistant_msg and len(assistant_msg['content']) > 200 else assistant_msg['content'] if assistant_msg else ''
                }
                summaries.append(summary)
        
        return jsonify({
            'summaries': summaries,
            'total': len(summaries)
        })
        
    except Exception as e:
        print(f"チャット概要取得エラー: {str(e)}")
        return jsonify({'error': f'チャット概要取得中にエラーが発生しました: {str(e)}'}), 500

@knowledge_bp.route('/stats', methods=['GET'])
def get_stats():
    """統計情報を取得"""
    try:
        # サービス別統計を計算
        service_stats = {}
        for msg in chat_data['messages']:
            service = msg['service']
            if service not in service_stats:
                service_stats[service] = {'messages': 0, 'conversations': 0}
            service_stats[service]['messages'] += 1
        
        for conv in chat_data['conversations']:
            service = conv['service']
            if service in service_stats:
                service_stats[service]['conversations'] += 1
        
        return jsonify({
            'total_messages': chat_data['stats']['messages'],
            'total_conversations': chat_data['stats']['conversations'],
            'total_searches': chat_data['stats']['searches'],
            'service_breakdown': service_stats
        })
        
    except Exception as e:
        print(f"統計情報取得エラー: {str(e)}")
        return jsonify({'error': f'統計情報取得中にエラーが発生しました: {str(e)}'}), 500

@knowledge_bp.route('/services', methods=['GET'])
def get_supported_services():
    """サポートされているAIサービス一覧を取得"""
    return jsonify({
        'services': [
            {'id': 'chatgpt', 'name': 'ChatGPT', 'formats': ['JSON']},
            {'id': 'claude', 'name': 'Claude', 'formats': ['Text']},
            {'id': 'gemini', 'name': 'Gemini', 'formats': ['Text']},
            {'id': 'grok', 'name': 'Grok', 'formats': ['Text']},
            {'id': 'openai_api', 'name': 'OpenAI API', 'formats': ['JSON']}
        ]
    })

@knowledge_bp.route('/clear', methods=['POST'])
def clear_data():
    """データをクリア（デバッグ用）"""
    try:
        chat_data['messages'] = []
        chat_data['conversations'] = []
        chat_data['stats'] = {'messages': 0, 'conversations': 0, 'searches': 0}
        
        return jsonify({
            'success': True,
            'message': 'データがクリアされました'
        })
    except Exception as e:
        return jsonify({'error': f'データクリア中にエラーが発生しました: {str(e)}'}), 500

