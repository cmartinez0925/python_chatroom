import errno
import datetime
import ipaddress
import logging
import socket

from contextlib import suppress
from zoneinfo import ZoneInfo

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# log_handler = logging.FileHandler('server.log')
# log_formatter = logging.Formatter('%(filename)s:%(name)s:%(message)s')
# log_handler.setFormatter(log_formatter)
# logger.addHandler(log_handler)

class Server():
    #Class Constants
    BACKLOG = 10
    DATASIZE = 4096
    ENCODING = 'ISO-8859-1'
    MAX_CLIENTS = 100
    MAX_CLIENTS_REACHED_MSG = (
    "Server has reached the maximum amount of clients."
    "Please try again later."
    )
    MAX_USERNAME_SIZE = 20
    TIME_FORMAT = '[%b %d, %Y - %H:%M:%S]'
    TIME_ZONE = 'US/Eastern'
    WELCOME_MSG = "Welcome to Link's Chatroom!"
    
    #Constructor
    def __init__(self, host: str, port: int, 
                 client_map:dict[socket.socket, str]=None):
        """Constructor for server class"""
        self.host = self.validate_host(host)
        self.port = self.validate_port(port)
        self.addr = (self.host, self.port)
        self.client_map = dict(client_map) if client_map is not None else {}
        self.sock = self.setup_socket()

    #Methods
    def accept_connection(self) -> tuple[socket.socket, str, int]:
        """Accept connections, essentially a wrapper for socket.accept()"""
        client, addr = self.sock.accept()
        host, port = addr
        return client, host, port


    def add_client(self, client: socket.socket, username: str) -> bool:
        #Lock this section to ensure proper count of clients
        if len(self.client_map) < self.MAX_CLIENTS:
            self.client_map[client] = username
            return True
        return False


    def ask_for_username(self, client: socket.socket) -> None:
        """Ask the client to send their desire username for the chat"""
        msg = f"{self.time_now()} Please enter your username:"
        client.sendall(msg.encode(self.ENCODING))


    def broadcast_msg(self, msg: str) -> None:
        """Send a broadcast message to all clients in the chatroom"""
        for connection in self.client_map.keys():
            connection.sendall(msg.encode(self.ENCODING))


    def close_all_connections(self) -> None:
        """Close all the connections"""
        connections_to_close = dict(self.client_map)
        self.client_map.clear()
        for connection in connections_to_close.keys():
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()


    def disconnect_client(self, client: socket.socket) -> None:
        """Remove the client from the chatroom and notify the chat"""
        username = self.client_map.pop(client, None)
        try:
            client.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            if e.errno not in (errno.ENOTCONN, errno.EBADF):
                raise
        finally:
            with suppress(OSError):
                client.close()

        #Never had the user registered, so nothing to broadcast
        if not username:
            return
        
        remove_user_msg = f"{self.time_now()} {username} has disconnected."
        
        for connection in self.client_map.keys():
            connection.sendall(remove_user_msg.encode(self.ENCODING))


    def is_there_room(self) -> bool:
        """Let's you know if server is full"""
        if len(self.client_map) < self.MAX_CLIENTS:
            return True
        return False

    def listen_for_connections(self) -> None:
        """Listens for connections, provides msg and log input"""
        ### NEED TO IMPLEMENT LOGGING CAPE ###
        print(f"{self.time_now()} Listening for connections on {self.addr}")
        self.sock.listen(self.BACKLOG)


    def max_capacity_notification(self, client: socket.socket) -> None:
        """Let client know the server is maxed out, try again later"""
        client.sendall(self.MAX_CLIENTS_REACHED_MSG.encode(self.ENCODING))


    def new_user_notification(self, client: socket.socket) -> None:
        """Notify chatroom that a new user has enter the chat"""
        new_user_msg = f"{self.time_now()} {self.client_map[client]} "
        new_user_msg += "has entered the chat."
        for connection in self.client_map.keys():
            if connection is not client:
                connection.sendall(new_user_msg.encode(self.ENCODING))


    def process_username(self, client: socket.socket) -> str:
        """Process the client's username"""
        data = client.recv(self.DATASIZE)
        username = data.decode(self.ENCODING).strip()

        if len(username) > self.MAX_USERNAME_SIZE:
            return username[:self.MAX_USERNAME_SIZE]
        elif not username:
            username = f"User_{len(self.client_map)}"

        return username
    

    def send_welcome_msg(self, client: socket.socket, username: str) -> None:
        """Welcome the new user to the chatroom"""
        msg = f"{self.time_now()} {self.WELCOME_MSG}\nUsername is {username}"
        client.sendall(msg.encode(self.ENCODING))


    def setup_socket(self) -> socket.socket:
        """This will setup the socket options and listen for connections"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(self.addr)
        return server_socket


    def time_now(self) -> str:
        """Gets the current time and date in specific format"""
        return datetime.datetime.now(
            tz=ZoneInfo(self.TIME_ZONE)).strftime(self.TIME_FORMAT)
    

    @staticmethod
    def validate_host(host: str) -> str:
        """Validates if the host is a proper IPv4 address format"""
        ipaddress.IPv4Address(host)
        return host


    @staticmethod
    def validate_port(port: int) -> int:
        """Validates if port value is between 1024-65535 inclusive"""
        if not isinstance(port, int):
            raise TypeError(f"Port must be int, got {type(port).__name__}")
        if port < 0 or port > 65535:
            raise ValueError(f"Port out of range: {port}")
        if 1 <= port <= 1023:
            raise ValueError(f"Ports 1–1023 are reserved: {port}")
        return port
