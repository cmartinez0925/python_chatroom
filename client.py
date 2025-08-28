import argparse
import errno
import socket
import sys
import threading

from contextlib import suppress

ENCODING = "ISO-8859-1"
DATA_SIZE = 4096
TIMEOUT = 1

stop_thread = threading.Event()

def receive_messages(sock):
    try:
        while stop_thread.is_set() == False:
            try:
                data = sock.recv(DATA_SIZE)
            except ConnectionResetError as e:
                print(f"Connection Reset Error: {e}")
                break
            except OSError as e:
                print(f"OS Error: {e}")
                break

            if not data:
                print("\n[Server] disconnected")
                break

            try:
                print(data.decode(ENCODING))
            except Exception as e:
                print(f"Error decoding: {e}")
    finally:
        stop_thread.set()

def send_messages(sock):
    try:
        while stop_thread.is_set() == False:
            data = input()
            if data == "":
                data = '\n'
            sock.sendall(data.encode(ENCODING))
    except Exception as e:
        print(f"Error sending data to server: {e}")
    finally:
        stop_thread.set()

def main():
    parser = argparse.ArgumentParser(description="Chatroom Webserver")
    parser.add_argument(
        "-p", "--port", dest="port", type=int, default=8080,
        help="Port to listen for client connections (Default: 8080)"
    )
    parser.add_argument(
        "-a", "--addr", dest="addr", type=str, default="127.0.0.1",
         help="Address that clients are connecting to (Default: localhost)"
    )
    
    args = parser.parse_args()
    PORT = args.port
    ADDR = args.addr
    SERVER_ADDR = (ADDR, PORT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.settimeout(TIMEOUT)

    #Attempt to connect, if unable exit program
    try:
        sock.connect(SERVER_ADDR)
    except ConnectionRefusedError as e:
        print(f"Unable to connect to {SERVER_ADDR}: {e}")
        sys.exit(1)
    
    try:
        thread_recv = threading.Thread(
            target=receive_messages, 
            args=(sock,), 
            daemon=True
        )

        thread_send = threading.Thread(
            target=send_messages, 
            args=(sock,), 
            daemon=True
        )
    
        thread_recv.start()
        thread_send.start()

        thread_recv.join()
    except KeyboardInterrupt as e:
        print(f"\nTerminating the connection...")
    finally:
        stop_thread.set()
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            if e.errno not in (errno.ENOTCONN, errno.EBADF):
                print(f"Error shutting down socket: {e}")
                raise
        finally:
            thread_recv.join(timeout=TIMEOUT)
            thread_send.join(timeout=TIMEOUT)

            with suppress(OSError):
                sock.close()
                print("\nConnection terminated.")

if __name__ == '__main__':
    main()
