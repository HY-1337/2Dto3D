using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

// 用于解析 JSON 的数据结构
[Serializable]
public class AgentResponse
{
    public string trigger;
    public string reply;
}

[Serializable]
public class UserRequest
{
    public string text;
}

[RequireComponent(typeof(Animator))]
public class AvatarController : MonoBehaviour
{
    [Header("WebSocket Configuration")]
    public string serverUrl = "ws://127.0.0.1:8765";
    
    [Header("Test Input")]
    public string testMessage = "你好，跟我招个手吧";
    public bool sendTestMessage = false;

    private ClientWebSocket webSocket = null;
    private Animator animator;
    private CancellationTokenSource cancellationTokenSource;

    private void Start()
    {
        animator = GetComponent<Animator>();
        ConnectToServer();
    }

    private void Update()
    {
        // 测试逻辑：在 Inspector 勾选 sendTestMessage 时发送
        if (sendTestMessage)
        {
            sendTestMessage = false;
            SendTextMessage(testMessage);
        }
    }

    private async void ConnectToServer()
    {
        webSocket = new ClientWebSocket();
        cancellationTokenSource = new CancellationTokenSource();

        try
        {
            Uri uri = new Uri(serverUrl);
            Debug.Log($"[AvatarController] Connecting to {serverUrl} ...");
            await webSocket.ConnectAsync(uri, cancellationTokenSource.Token);
            Debug.Log("[AvatarController] Connected!");

            // 开始后台接收消息
            _ = ReceiveMessages();
        }
        catch (Exception e)
        {
            Debug.LogError($"[AvatarController] Connection Error: {e.Message}");
        }
    }

    private async Task ReceiveMessages()
    {
        var buffer = new byte[1024 * 4];

        while (webSocket.State == WebSocketState.Open)
        {
            try
            {
                var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationTokenSource.Token);
                
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    Debug.Log("[AvatarController] Server closed connection.");
                    await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                }
                else
                {
                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    Debug.Log($"[AvatarController] Received: {message}");
                    
                    // 解析 JSON 并在主线程触发动画
                    HandleServerResponse(message);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[AvatarController] Receive Error: {e.Message}");
                break;
            }
        }
    }

    public async void SendTextMessage(string text)
    {
        if (webSocket == null || webSocket.State != WebSocketState.Open)
        {
            Debug.LogWarning("[AvatarController] WebSocket is not connected.");
            return;
        }

        // 构造 JSON 发送
        UserRequest req = new UserRequest { text = text };
        string jsonRequest = JsonUtility.ToJson(req);
        
        byte[] bytes = Encoding.UTF8.GetBytes(jsonRequest);
        await webSocket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancellationTokenSource.Token);
        
        Debug.Log($"[AvatarController] Sent: {jsonRequest}");
    }

    private void HandleServerResponse(string json)
    {
        try
        {
            AgentResponse response = JsonUtility.FromJson<AgentResponse>(json);
            
            // Unity 的相关操作（如操作 Animator）必须在主线程中进行
            // 此处由于 await WebSocket 是异步的，可能不在主线程。
            // 简单的处理方式是使用 MainThreadDispatcher，或者在 Update 中轮询。
            // 现代 Unity 的 async/await (SynchronizationContext) 通常会自动回到主线程，但保险起见：
            
            // 播放动画
            if (!string.IsNullOrEmpty(response.trigger))
            {
                // 先重置一些可能冲突的 Trigger (可选)
                animator.ResetTrigger("Idle");
                animator.ResetTrigger("Walk");
                animator.ResetTrigger("Wave");
                animator.ResetTrigger("Talk");
                
                // 触发新的动画
                animator.SetTrigger(response.trigger);
                Debug.Log($"[AvatarController] Triggered Animation: {response.trigger}");
            }

            // 输出数字人的回复
            if (!string.IsNullOrEmpty(response.reply))
            {
                Debug.Log($"[AvatarReply] {response.reply}");
                // 如果你有 UI Text 或语音合成 (TTS)，可以在这里调用
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[AvatarController] JSON Parse Error: {e.Message}");
        }
    }

    private void OnDestroy()
    {
        if (webSocket != null)
        {
            cancellationTokenSource?.Cancel();
            webSocket.Dispose();
        }
    }
}
