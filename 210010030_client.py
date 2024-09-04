import socket
import threading
import os
import rsa
import cv2
import numpy as np
import traceback
import json

# Client socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', 8000))

# For Client name
client_socket.recv(1024).decode()
client_name = input("Enter your name: ")
client_socket.send(client_name.encode())

# For Public key
client_socket.recv(1024).decode()
(public_key, private_key) = rsa.newkeys(1024)
client_public_key = str(public_key.n) + "," + str(public_key.e)
client_socket.send(client_public_key.encode())

# Dictionary to store other clients' public keys
client_public_keys = {}

# To stop receiver when quit
stop_receiver = False


def receive():
    global stop_receiver
    global client_public_keys
    try:
        while True:
            message = client_socket.recv(1024).decode()
            if message.startswith("NEW_CLIENT:"):
                # Extract the new client's name and public key
                _, new_client_name, new_client_public_key = message.split(":")
                client_public_keys[new_client_name] = new_client_public_key
                print(f"{new_client_name} has joined the chat.")
            elif message.startswith("LEFT:"):
                # Extract the departed client's name
                _, departed_client_name = message.split(":")
                del client_public_keys[departed_client_name]
                print(f"{departed_client_name} has left the chat.")
            elif message.startswith("ENCRYPTED:"):
                # Extract the encrypted message and the sender's name
                _, sender_name = message.split(":")
                encrypted_message = client_socket.recv(1024)

                # Decrypt the message using the client's private key
                try:
                    decrypted_message = rsa.decrypt(encrypted_message, private_key).decode()
                    print(f"{sender_name}: {decrypted_message}")
                except rsa.pkcs1.DecryptionError as e:
                    print("Decryption failed:", e)
            elif message.startswith("AVAILABLE_VIDEOS:"):
                # Extract the list of available videos
                _, video_list = message.split(":")
                print("\nAvailable videos:")
                print(video_list)
            elif message.startswith("VIDEO"):
                message_frame = None
                cv2.namedWindow("Video", cv2.WINDOW_NORMAL)
                while True:
                    message_frame = client_socket.recv(1024 * 1024)
                    if message_frame == b"END_OF_VIDEO":
                        cv2.destroyAllWindows()
                        print("End of video stream.")
                        break

                    if message_frame != None:
                        # Receive and display the video frame
                        frame = cv2.imdecode(np.frombuffer(
                            message_frame, np.uint8), cv2.IMREAD_COLOR)
                        # print(frame)
                        if type(frame) != type(None) and frame.size > 0:
                            cv2.imshow("Video", frame)
                            cv2.waitKey(1)

            elif stop_receiver:
                client_socket.close()
                break
            else:
                client_public_keys=json.loads(message)
                print("updated")
                

    except Exception as e:
        print("An error occurred.", e)
        print(traceback.format_exc())
        client_socket.send("QUIT".encode())
        client_socket.close()


def write():
    global stop_receiver
    global client_public_keys
    help_message = '''message - this ask for receiver name and message and sends to the server
list - this will list the videos
play <video name> - this play the video if present in the server, just mention the video name without any quality or extension
quit - to exit the client program
clients - provides list of clients present in the server
help - will display this message
'''
    print("\nAvailable Commands: ")
    print(help_message)

    while True:
        cmd = input().strip()
        if cmd == "help":
            print(help_message)
        elif cmd == "message":
            for client in client_public_keys:
                print(client)
            receiver_name = input("Enter Receiver's name: ")
            message = input("Message: ")
            receiver_public_key = client_public_keys[receiver_name]
            n, e = map(int, receiver_public_key.split(","))
            receiver_public_key = rsa.PublicKey(n, e)

            encrypted_message = rsa.encrypt(
                message.encode(), receiver_public_key)
            client_socket.send(
                f"ENCRYPTED:{client_name}".encode())
            # Send the encrypted message to the server
            client_socket.send(encrypted_message)
        elif cmd == "list":
            client_socket.send("LIST_VIDEOS".encode())
        elif cmd.startswith("play"):
            video_name = cmd.split(" ")[1]
            client_socket.send(f"PLAY_VIDEO:{video_name}".encode())
        elif cmd == "quit":
            client_socket.send("QUIT".encode())
            stop_receiver = True
            break
        elif cmd == "clients":
            for client in client_public_keys:
                print(client)


# Start the receive and write threads
receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()
