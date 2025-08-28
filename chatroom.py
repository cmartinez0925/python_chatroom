import argparse
import socket
import sys
import threading
import server

CLIENTS_LOCK = threading.Lock()

def handle_client(client: socket.socket, serv: server.Server) -> None:
    serv.ask_for_username(client)
    username = serv.process_username(client)

    with CLIENTS_LOCK:
        client_added = serv.add_client(client=client, username=username)

    if client_added:
        try:
            with CLIENTS_LOCK:
                serv.new_user_notification(client)
                serv.send_welcome_msg(client, username)
        except Exception as e:
            with CLIENTS_LOCK:
                serv.disconnect_client(client)
    else:
        with CLIENTS_LOCK:
            serv.disconnect_client(client)
        return
    
    try:
        while True:
            try:
                data = client.recv(serv.DATASIZE)
            except ConnectionError as e:
                print(f"{serv.time_now()} {username} - Connection Error: {e}")
                break
            except OSError as e:
                print(f"{serv.time_now()} {username} - OS Error: {e}")
                break

            if not data:
                print(f"{serv.time_now()} {username}: Connection closed.")
                break

            try:
                msg = data.decode(serv.ENCODING)
            except OSError as e:
                print(f"{serv.time_now()} {username} - Error decoding: {e}")
            print(f"{serv.time_now()} {username}: {msg}") #Logging here maybe?

            #Now we must broadcast to other clients
            with CLIENTS_LOCK:
                targets = dict(serv.client_map)
            for conn, u_name in targets.items():
                if conn is not client:
                    try:
                        data = f"{serv.time_now()} {username}: {msg}".encode(
                            serv.ENCODING)
                        conn.sendall(data)
                    except OSError as e:
                        print(f"{serv.time_now()} {u_name} - Error sending: {e}")
                        serv.disconnect_client(conn)
    finally:
        serv.disconnect_client(client)

def main():
    parser = argparse.ArgumentParser(description="Chatroom Server")
    
    parser.add_argument(
        "-a", "--addr", dest="addr", type=str, default="127.0.0.1",
         help="Address that clients are connecting to (Default: localhost)"
    )
    
    parser.add_argument(
        "-p", "--port", dest="port", type=int, default=8080,
        help="Port to listen for client connections (Default: 8080)"
    )

    
    args = parser.parse_args()
    HOST = args.addr
    PORT = args.port

    try:
        serv = server.Server(host=HOST, port=PORT)
    except Exception as e:
        print(f"Unable to create the server: {e}")
        sys.exit(1)

    serv.listen_for_connections()
    
    #Create separate threads for each client that connects
    try:
        while True:
            client, _, _ = serv.accept_connection()
            with CLIENTS_LOCK:
                server_has_room = serv.is_there_room()
            if server_has_room:
                #If client added, we need to create a thread to handle the work
                thread = threading.Thread(
                    target=handle_client,
                    args=(client, serv),
                    daemon=True
                )
                thread.start()
            else:
                try:
                    serv.max_capacity_notification(client)
                except OSError as e:
                    print(f"{serv.time_now()} Error max capacity message: {e}")
                finally:
                    serv.disconnect_client(client)
    except KeyboardInterrupt as e:
        print("\nServer has been terminated.")
        try:
            serv.close_all_connections()
        except Exception as e:
            print(f"{serv.time_now()} Unable to close all connections: {e}")
    finally:
        serv.sock.close()


if __name__ == '__main__':
    main()