import socket
import threading
import os
import cv2
import json

# Server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 8000))
server_socket.listen(5)

# Dictionaries to store client info
client_dict = {}  # {client_name: public_key}
client_sockets = {}  # {client_name: client_socket}

# Video directory
video_dir = "videos"


def handle_client(conn, addr):
    global client_dict
    try:
        # Request client name and public key
        conn.send("CLIENT_NAME:".encode())
        client_name = conn.recv(1024).decode()
        conn.send("PUBLIC_KEY:".encode())
        client_public_key = conn.recv(1024).decode()

        # Store client info in dictionaries
        client_dict[client_name] = client_public_key
        client_sockets[client_name] = conn
        # Broadcast new client info to all connected clients except the new one
        broadcast(f"NEW_CLIENT:{client_name}:{client_public_key}", client_name)
        mess=json.dumps(client_dict)
        for nam in client_sockets:
            client_sockets[nam].send(mess.encode())
        # conn.send()

        # Handle client messages
        while True:
            message = conn.recv(1024).decode()
            if message.startswith("ENCRYPTED:"):
                # Broadcast the encrypted message to all clients
                encrypted_message = conn.recv(1024)
                broadcast(message, client_name, encrypted_message)
            elif message == "LIST_VIDEOS":
                # Send the list of available videos
                video_files = os.listdir(video_dir)
                video_list = "\n".join(video_files)
                conn.send(f"AVAILABLE_VIDEOS:{video_list}".encode())
            elif message.startswith("PLAY_VIDEO:"):
                # Stream the requested video
                video_name = message.split(":")[1]
                stream_video(conn, video_name)
            elif message == "QUIT":
                index = list(client_sockets.values()).index(conn)
                client_name = list(client_sockets.keys())[index]
                del client_dict[client_name]
                del client_sockets[client_name]
                conn.close()
                broadcast(f"LEFT:{client_name}", client_name)
                break
            else:
                # Handle other messages
                pass
    except:
        pass


def receive():
    while True:
        conn, addr = server_socket.accept()
        print(f"Connected with {str(addr)}")

        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

def broadcast(message, sender_name, encrypted_message=None):
    for name, socket in client_sockets.items():
        if name != sender_name:
            try:
                socket.send(message.encode())
                if encrypted_message:
                    socket.send(encrypted_message)
            except:
                index = list(client_sockets.values()).index(socket)
                name = list(client_sockets.keys())[index]
                del client_dict[name]
                del client_sockets[name]
                socket.close()


def stream_video(conn, video_name):
    video_path = os.path.join(video_dir, video_name)

    # Assuming the video files are named in the format: video_name_240p.mp4, video_name_720p.mp4, video_name_1440p.mp4
    resolutions = ["240p", "480p", "720p"]

    for i in range(len(resolutions)):
        resolution = resolutions[i]
        file_name = f"{video_name}_{resolution}.mp4"
        file_path = os.path.join(video_dir, file_name)

        # Open the video file using OpenCV
        cap = cv2.VideoCapture(file_path)

        # Read and send one-third of the frames from this resolution
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        start = (frame_count // 3)*i
        end = (frame_count // 3)*(i+1)
        cap.set(cv2.CAP_PROP_POS_FRAMES,start)
        for _ in range(start, end):
            ret, frame = cap.read()
            if ret:
                # Encode the frame as JPEG and send it to the client
                success, frame_bytes = cv2.imencode('.jpg', frame)
                conn.send("VIDEO".encode())
                conn.send(frame_bytes.tobytes())

        # Release the video capture object
        cap.release()

    # Send the "END_OF_VIDEO" message to the client
    conn.send("END_OF_VIDEO".encode())


print("Server is running...")
receive()
