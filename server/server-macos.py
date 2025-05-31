import socket
import json
import time
import threading
import psutil

def get_system_stats():
    try:
        cpu_freq = psutil.cpu_freq()
        current_freq = cpu_freq.current if cpu_freq and cpu_freq.current else 0
    except Exception as e:
        print(f"获取 CPU 频率时出错: {e}")
        current_freq = 0
    return {
        'cpu': {
            'percent': psutil.cpu_percent(interval=None),
            'per_cpu': psutil.cpu_percent(interval=None, percpu=True),
            'freq': current_freq
        },
        'memory': {
            'used': psutil.virtual_memory().used,
            'total': psutil.virtual_memory().total,
            'percent': psutil.virtual_memory().percent
        },
        'network': {
            'bytes_sent': psutil.net_io_counters().bytes_sent,
            'bytes_recv': psutil.net_io_counters().bytes_recv,
            'upload_speed': 0,
            'download_speed': 0
        }
    }

def handle_client(conn, addr):
    print(f"新的连接来自: {addr}")
    last_bytes_sent = 0
    last_bytes_recv = 0
    last_time = time.time()
    
    try:
        while True:
            current_stats = get_system_stats()
            
            now = time.time()
            time_diff = now - last_time
            if time_diff > 0:
                current_stats['network']['upload_speed'] = (
                    (current_stats['network']['bytes_sent'] - last_bytes_sent) / time_diff
                )
                current_stats['network']['download_speed'] = (
                    (current_stats['network']['bytes_recv'] - last_bytes_recv) / time_diff
                )
            
            last_bytes_sent = current_stats['network']['bytes_sent']
            last_bytes_recv = current_stats['network']['bytes_recv']
            last_time = now
            
            try:
                data = json.dumps(current_stats).encode('utf-8') + b'\n'
                conn.sendall(data)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                print(f"客户端 {addr} 断开连接: {e}")
                break
            except Exception as e:
                print(f"发送数据到 {addr} 时出错: {e}")
                break
                
            time.sleep(1)
            
    except Exception as e:
        print(f"处理客户端 {addr} 时发生错误: {e}")
    finally:
        conn.close()
        print(f"与 {addr} 的连接已关闭")

def start_server(host='0.0.0.0', port=5021):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        print(f"服务器启动，监听 {host}:{port}")
        print("made by EXE_autumnwind 版本:2.0[MacOS优化版]")
        
        while True:
            try:
                conn, addr = s.accept()
                client_thread = threading.Thread(
                    target=handle_client, 
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                print(f"接受新连接时出错: {e}")
                time.sleep(1)

if __name__ == "__main__":
    start_server()
