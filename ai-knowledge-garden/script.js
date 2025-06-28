// AI Knowledge Garden - Main JavaScript File
// 複数のAIチャットサービスのログを横断的に検索するWebアプリケーション

// ========================================
// DOM Elements
// ========================================
const fileInput = document.getElementById('file-input');
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const resultsContainer = document.getElementById('results-container');

// ========================================
// Global Variables
// ========================================
let uploadedFiles = []; // アップロードされたファイルの配列
let processedLogs = []; // 処理済みのログデータの配列
let currentSearchResults = []; // 現在の検索結果
let allConversations = []; // 正規化された全会話データ

// ========================================
// Event Listeners
// ========================================

// ファイルアップロードのイベントリスナー
fileInput.addEventListener('change', handleFileUpload);

// 検索入力のイベントリスナー（リアルタイム検索）
searchInput.addEventListener('input', handleSearch);

// 検索ボタンのイベントリスナー
searchButton.addEventListener('click', () => {
    const query = searchInput.value.trim();
    if (query) {
        performSearch(query);
    }
});

// Enterキーでの検索実行
searchInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
            performSearch(query);
        }
    }
});

// ========================================
// Core Functions
// ========================================

/**
 * ファイルアップロード処理（非同期）
 * @param {Event} event - ファイル選択イベント
 */
async function handleFileUpload(event) {
    console.log('handleFileUpload triggered');
    
    const files = Array.from(event.target.files);
    console.log('Selected files:', files);
    
    if (files.length === 0) {
        console.log('No files selected');
        return;
    }
    
    // ファイル情報を表示
    displayFileInfo(files);
    
    // 最初のファイルを処理（ChatGPTファイルを想定）
    const firstFile = files[0];
    console.log('Processing first file:', firstFile.name);
    
    try {
        const content = await readFileAsText(firstFile);
        console.log('File content read successfully');
        
        // ChatGPTファイルの場合の処理
        if (firstFile.name.includes('conversations.json') || firstFile.name.endsWith('.json')) {
            const normalizedData = await parseChatGPTLog(content);
            console.log('ChatGPT log parsed successfully:', normalizedData);
            
            // 正規化されたデータをグローバル変数に保存
            allConversations = normalizedData;
            processedLogs = normalizedData;
            
            // 処理結果を表示
            displayProcessingResult(normalizedData.length);
        } else {
            console.log('Unsupported file format for first file');
        }
        
    } catch (error) {
        console.error('Error processing file:', error);
        displayMessage('ファイルの処理中にエラーが発生しました。', 'error');
    }
}

/**
 * ファイルをテキストとして読み込む
 * @param {File} file - 読み込むファイル
 * @returns {Promise<string>} ファイルの内容
 */
function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(e);
        reader.readAsText(file);
    });
}

/**
 * ChatGPTのログファイルを解析して正規化する
 * @param {string} jsonContent - ChatGPTのJSONファイルの内容
 * @returns {Promise<Array>} 正規化された会話データの配列
 */
async function parseChatGPTLog(jsonContent) {
    console.log('Starting ChatGPT log parsing...');
    
    try {
        // JSONをパース
        const data = JSON.parse(jsonContent);
        console.log('JSON parsed successfully');
        
        const normalizedConversations = [];
        
        // ChatGPTのエクスポートファイルの構造に基づいて解析
        // 一般的な構造: { conversations: [...] } または直接配列
        let conversations = [];
        
        if (data.conversations) {
            // conversationsプロパティが存在する場合
            conversations = data.conversations;
            console.log(`Found ${conversations.length} conversations in conversations property`);
        } else if (Array.isArray(data)) {
            // 直接配列の場合
            conversations = data;
            console.log(`Found ${conversations.length} conversations in root array`);
        } else {
            console.log('Unexpected data structure:', Object.keys(data));
            return [];
        }
        
        // 各会話を処理
        conversations.forEach((conversation, conversationIndex) => {
            console.log(`Processing conversation ${conversationIndex + 1}/${conversations.length}`);
            
            // 会話の基本情報を取得
            const conversationId = conversation.id || conversation.conversation_id || `conv_${conversationIndex}`;
            const title = conversation.title || conversation.conversation_title || `会話 ${conversationIndex + 1}`;
            const createTime = conversation.create_time || conversation.created_at || null;
            
            // メッセージを取得
            let messages = [];
            
            if (conversation.messages) {
                messages = conversation.messages;
            } else if (conversation.mapping) {
                // mapping形式の場合（新しいChatGPTエクスポート形式）
                messages = extractMessagesFromMapping(conversation.mapping);
            } else if (conversation.current_node) {
                // current_node形式の場合
                messages = extractMessagesFromCurrentNode(conversation.current_node);
            }
            
            console.log(`Found ${messages.length} messages in conversation ${conversationIndex + 1}`);
            
            // 各メッセージを正規化
            messages.forEach((message, messageIndex) => {
                const normalizedMessage = normalizeChatGPTMessage(message, conversationId, title, createTime, messageIndex);
                if (normalizedMessage) {
                    normalizedConversations.push(normalizedMessage);
                }
            });
        });
        
        console.log(`Successfully normalized ${normalizedConversations.length} messages from ChatGPT log`);
        return normalizedConversations;
        
    } catch (error) {
        console.error('Error parsing ChatGPT log:', error);
        throw new Error('ChatGPTログファイルの解析に失敗しました: ' + error.message);
    }
}

/**
 * ChatGPTのメッセージを正規化する
 * @param {Object} message - 元のメッセージオブジェクト
 * @param {string} conversationId - 会話ID
 * @param {string} title - 会話タイトル
 * @param {string} createTime - 作成時刻
 * @param {number} messageIndex - メッセージインデックス
 * @returns {Object|null} 正規化されたメッセージ
 */
function normalizeChatGPTMessage(message, conversationId, title, createTime, messageIndex) {
    try {
        // メッセージの基本情報を取得
        const role = message.role || message.author?.role || 'unknown';
        let content = '';

        // contentまたはtextプロパティの型に応じて処理
        if (typeof message.content === 'string') {
            content = message.content;
        } else if (typeof message.content === 'object' && message.content !== null) {
            // ChatGPTの新しい形式: { content_type: 'text', parts: [...] }
            if (Array.isArray(message.content.parts)) {
                content = message.content.parts.join('\n');
            }
        } else if (typeof message.text === 'string') {
            content = message.text;
        } else if (typeof message.text === 'object' && message.text !== null) {
            if (Array.isArray(message.text.parts)) {
                content = message.text.parts.join('\n');
            }
        }

        // ロールを統一
        let speaker = 'unknown';
        if (role === 'user' || role === 'human') {
            speaker = 'user';
        } else if (role === 'assistant' || role === 'gpt') {
            speaker = 'assistant';
        } else if (role === 'system') {
            speaker = 'system';
        }

        // タイムスタンプを処理
        let timestamp = '';
        if (message.create_time) {
            timestamp = new Date(message.create_time * 1000).toISOString();
        } else if (message.timestamp) {
            timestamp = new Date(message.timestamp).toISOString();
        } else if (createTime) {
            timestamp = new Date(createTime * 1000).toISOString();
        } else {
            timestamp = new Date().toISOString();
        }

        // 正規化されたオブジェクトを作成
        const normalizedMessage = {
            platform: 'chatgpt',
            speaker: speaker,
            text: content || '',
            timestamp: timestamp,
            conversationId: conversationId,
            conversationTitle: title,
            messageIndex: messageIndex,
            originalMessage: message // デバッグ用に元のメッセージも保持
        };

        return normalizedMessage;

    } catch (error) {
        console.error('Error normalizing message:', error);
        return null;
    }
}

/**
 * mapping形式からメッセージを抽出
 * @param {Object} mapping - ChatGPTのmappingオブジェクト
 * @returns {Array} メッセージの配列
 */
function extractMessagesFromMapping(mapping) {
    const messages = [];
    
    // mappingの各ノードを処理
    Object.values(mapping).forEach(node => {
        if (node.message) {
            messages.push(node.message);
        }
    });
    
    // タイムスタンプ順にソート
    messages.sort((a, b) => {
        const timeA = a.create_time || 0;
        const timeB = b.create_time || 0;
        return timeA - timeB;
    });
    
    return messages;
}

/**
 * current_node形式からメッセージを抽出
 * @param {Object} currentNode - ChatGPTのcurrent_nodeオブジェクト
 * @returns {Array} メッセージの配列
 */
function extractMessagesFromCurrentNode(currentNode) {
    const messages = [];
    
    // 再帰的にメッセージを収集
    function collectMessages(node) {
        if (node.message) {
            messages.push(node.message);
        }
        
        if (node.children) {
            node.children.forEach(child => {
                collectMessages(child);
            });
        }
    }
    
    collectMessages(currentNode);
    
    // タイムスタンプ順にソート
    messages.sort((a, b) => {
        const timeA = a.create_time || 0;
        const timeB = b.create_time || 0;
        return timeA - timeB;
    });
    
    return messages;
}

/**
 * 処理結果を表示
 * @param {number} messageCount - 処理されたメッセージ数
 */
function displayProcessingResult(messageCount) {
    const fileInfo = document.querySelector('.file-info');
    if (fileInfo) {
        fileInfo.textContent = `${messageCount}個のメッセージが正常に処理されました`;
        fileInfo.style.color = '#4caf50';
    }
    
    // 結果コンテナに処理完了メッセージを表示
    resultsContainer.innerHTML = `
        <div class="empty-state">
            <p>✅ ${messageCount}個のメッセージが読み込まれました</p>
            <p>キーワードを入力して検索を開始してください</p>
        </div>
    `;
}

/**
 * 検索処理
 * @param {Event} event - 検索入力イベント
 */
function handleSearch(event) {
    console.log('handleSearch triggered');
    
    const query = event.target.value.trim();
    console.log('Search query:', query);
    
    if (query.length === 0) {
        clearResults();
        return;
    }
    
    // リアルタイム検索（デバウンス機能付き）
    debounceSearch(query);
}

/**
 * ファイル情報を表示
 * @param {File[]} files - 選択されたファイルの配列
 */
function displayFileInfo(files) {
    const fileInfo = document.querySelector('.file-info');
    if (fileInfo) {
        fileInfo.textContent = `${files.length}個のファイルが選択されました`;
        fileInfo.style.color = '#b0b0b0';
    }
}

/**
 * ファイルを処理
 * @param {File[]} files - 処理するファイルの配列
 */
function processFiles(files) {
    console.log('Processing files...');
    
    files.forEach((file, index) => {
        console.log(`Processing file ${index + 1}: ${file.name}`);
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const content = e.target.result;
                const processedData = parseFileContent(content, file.name);
                
                if (processedData) {
                    processedLogs.push(...processedData);
                    console.log(`Successfully processed ${file.name}`);
                }
            } catch (error) {
                console.error(`Error processing file ${file.name}:`, error);
            }
        };
        
        reader.readAsText(file);
    });
}

/**
 * ファイル内容を解析
 * @param {string} content - ファイルの内容
 * @param {string} fileName - ファイル名
 * @returns {Array|null} 解析されたログデータ
 */
function parseFileContent(content, fileName) {
    console.log(`Parsing content from ${fileName}`);
    
    try {
        // JSONファイルの場合
        if (fileName.endsWith('.json')) {
            const jsonData = JSON.parse(content);
            return normalizeJsonData(jsonData, fileName);
        }
        
        // テキストファイルの場合
        if (fileName.endsWith('.txt')) {
            return normalizeTextData(content, fileName);
        }
        
        // CSVファイルの場合
        if (fileName.endsWith('.csv')) {
            return normalizeCsvData(content, fileName);
        }
        
        console.log(`Unsupported file format: ${fileName}`);
        return null;
        
    } catch (error) {
        console.error(`Error parsing file ${fileName}:`, error);
        return null;
    }
}

/**
 * JSONデータを正規化
 * @param {Object} jsonData - JSONデータ
 * @param {string} fileName - ファイル名
 * @returns {Array} 正規化されたデータ
 */
function normalizeJsonData(jsonData, fileName) {
    console.log('Normalizing JSON data');
    
    // ここでChatGPT、Claude、Geminiの異なるJSON形式を統一
    // 将来的に実装予定
    return [];
}

/**
 * テキストデータを正規化
 * @param {string} textData - テキストデータ
 * @param {string} fileName - ファイル名
 * @returns {Array} 正規化されたデータ
 */
function normalizeTextData(textData, fileName) {
    console.log('Normalizing text data');
    
    // テキストファイルの解析ロジック
    // 将来的に実装予定
    return [];
}

/**
 * CSVデータを正規化
 * @param {string} csvData - CSVデータ
 * @param {string} fileName - ファイル名
 * @returns {Array} 正規化されたデータ
 */
function normalizeCsvData(csvData, fileName) {
    console.log('Normalizing CSV data');
    
    // CSVファイルの解析ロジック
    // 将来的に実装予定
    return [];
}

/**
 * 検索を実行
 * @param {string} query - 検索クエリ
 */
function performSearch(query) {
    console.log(`=== 検索開始 ===`);
    console.log(`検索クエリ: "${query}"`);
    console.log(`allConversations.length: ${allConversations.length}`);
    
    if (allConversations.length === 0) {
        console.log('❌ 会話データがありません');
        displayMessage('ファイルをアップロードしてから検索してください。', 'warning');
        return;
    }
    
    // 検索ロジック
    const results = searchInLogs(query);
    console.log(`検索結果: ${results.length}件`);
    
    displaySearchResults(results, query);
}

/**
 * ログ内を検索
 * @param {string} query - 検索クエリ
 * @returns {Array} 検索結果
 */
function searchInLogs(query) {
    console.log(`=== 検索処理開始 ===`);
    console.log(`検索対象: ${allConversations.length}件のメッセージ`);
    console.log(`検索語: "${query}"`);
    
    // 基本的なキーワード検索
    const results = allConversations.filter((conversation, index) => {
        const text = conversation.text.toLowerCase();
        const searchTerms = query.toLowerCase().split(' ').filter(term => term.length > 0);
        
        console.log(`メッセージ ${index + 1}: ${text.substring(0, 100)}...`);
        
        // すべての検索語が含まれているかチェック
        const matches = searchTerms.every(term => {
            const found = text.includes(term);
            console.log(`  検索語 "${term}": ${found ? '✅' : '❌'}`);
            return found;
        });
        
        if (matches) {
            console.log(`  ✅ メッセージ ${index + 1} がマッチしました`);
        }
        
        return matches;
    });
    
    console.log(`=== 検索完了 ===`);
    console.log(`マッチしたメッセージ: ${results.length}件`);
    
    // 最初の数件の結果を詳細表示
    results.slice(0, 3).forEach((result, index) => {
        console.log(`結果 ${index + 1}:`);
        console.log(`  スピーカー: ${result.speaker}`);
        console.log(`  テキスト: ${result.text.substring(0, 200)}...`);
        console.log(`  タイムスタンプ: ${result.timestamp}`);
    });
    
    return results;
}

/**
 * 検索結果を表示
 * @param {Array} results - 検索結果
 * @param {string} query - 検索クエリ
 */
function displaySearchResults(results, query) {
    console.log(`=== 結果表示開始 ===`);
    console.log(`表示する結果: ${results.length}件`);
    
    resultsContainer.innerHTML = '';
    
    if (results.length === 0) {
        console.log('検索結果が0件のため、メッセージを表示');
        displayMessage(`"${query}" に一致する結果が見つかりませんでした。`, 'info');
        return;
    }
    
    // 結果のヘッダーを表示
    const header = document.createElement('div');
    header.className = 'results-header';
    header.innerHTML = `<h3>検索結果: "${query}" (${results.length}件)</h3>`;
    resultsContainer.appendChild(header);
    
    console.log('各結果を表示中...');
    results.forEach((result, index) => {
        console.log(`結果 ${index + 1} を表示中...`);
        const resultElement = createResultElement(result);
        resultsContainer.appendChild(resultElement);
    });
    
    console.log(`=== 結果表示完了 ===`);
}

/**
 * 結果要素を作成
 * @param {Object} result - 結果データ
 * @returns {HTMLElement} 結果要素
 */
function createResultElement(result) {
    console.log('結果要素を作成中:', result);
    
    const div = document.createElement('div');
    div.className = 'result-item';
    
    // タイムスタンプを読みやすい形式に変換
    const date = new Date(result.timestamp);
    const formattedDate = date.toLocaleString('ja-JP');
    
    // スピーカーアイコンを設定
    const speakerIcon = result.speaker === 'user' ? '👤' : '🤖';
    const speakerLabel = result.speaker === 'user' ? 'ユーザー' : 'アシスタント';
    
    // テキストを安全に表示（HTMLエスケープ）
    const safeText = result.text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    div.innerHTML = `
        <div class="result-header">
            <span class="speaker-icon">${speakerIcon}</span>
            <span class="speaker-label">${speakerLabel}</span>
            <span class="timestamp">${formattedDate}</span>
        </div>
        <div class="result-content">${safeText}</div>
        <div class="result-meta">
            <span class="conversation-title">📝 ${result.conversationTitle}</span>
        </div>
    `;
    
    console.log('結果要素を作成完了');
    return div;
}

/**
 * メッセージを表示
 * @param {string} message - 表示するメッセージ
 * @param {string} type - メッセージタイプ ('info', 'warning', 'error')
 */
function displayMessage(message, type = 'info') {
    resultsContainer.innerHTML = `
        <div class="empty-state">
            <p>${message}</p>
        </div>
    `;
}

/**
 * 結果をクリア
 */
function clearResults() {
    if (allConversations.length > 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <p>キーワードを入力して検索を開始してください</p>
            </div>
        `;
    } else {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <p>ファイルをアップロードして検索を開始してください</p>
            </div>
        `;
    }
}

/**
 * 検索のデバウンス処理
 * @param {string} query - 検索クエリ
 */
let searchTimeout;
function debounceSearch(query) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300); // 300msのデバウンス
}

// ========================================
// Utility Functions
// ========================================

/**
 * アプリケーションの初期化
 */
function initializeApp() {
    console.log('AI Knowledge Garden initialized');
    console.log('Ready to process AI chat logs');
}

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', initializeApp);
