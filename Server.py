import queue
import threading
import socket

DONT_ECHO = True

class Server:
    def _client_id_gen():
        i = 0
        while True:
            yield i
            i += 1

    client_id = _client_id_gen()
    
    def __init__(self, ip, host):
        self.ip = ip
        self.host = host
        
        self.per_clients = []
        self.is_running = False
        self.all_threads_running = threading.Event()

        # Specific Details
        class ServerDetails:
            def __init__(self):
                self.persistent_identities = dict()
                self.persistent_messages = []
                
                self.new_identities = queue.Queue() # Clientside, this is used to populate a dictionary
                self.new_messages = queue.Queue()

                self.write_lock = threading.Lock()

            # TODO implement pruning if the persistents get too long, if that becomes a problem
            def prune_persistents(self):
                pass
            
            def add_identity(self, id, name):
                self.persistent_identities[id] = name
                self.new_identities.put((id, name))

            def add_message(self, id, contents):
                self.persistent_messages.append((id, contents))
                self.new_messages.put((id, contents))
            
        self.server_details = ServerDetails()

        # Threads
        self.acceptor_thread = threading.Thread(target=self.threaded_acceptor)
        self.prescriber_thread = threading.Thread(target=self.threaded_prescriber)
        
    def start(self):
        self.is_running = True
        self.acceptor_thread.start()
        self.prescriber_thread.start()

    def join(self):
        self.is_running = False
        self.acceptor_thread.join()
        self.prescriber_thread.join()

    # Awaits connections, and diverts them to new PerClient instances
    def threaded_acceptor(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.ip, self.host))
        print(f"Acceptor thread has bound a socket to {(self.ip, self.host)}")
        # Needed to start all threads instantly:
        self.all_threads_running.set()
        while self.is_running:
            sock.listen()
            conn, addr = sock.accept()
            print(f"Accepted connection from {addr}")

            new_perclient = PerClient(next(Server.client_id), conn, addr, self.all_threads_running, self.server_details)
            # Just start instantly
            new_perclient.start()
            self.per_clients.append(new_perclient)
            

    # When there are elements in the queues of server details, instructs the PerClients to distribute as nessesary
    def threaded_prescriber(self): # This could be improved by combining the queues into one, or by having one prescriber for every queue. Former is better, with elements being inherited instances of some base class.
        # hmm, should this do the heavy lifting here, or pass it onto the threaded sender to do?
        # i think everything that doesnt need to be done here should be deffered.
        # but actually its okay to have some unnecessarily work done here    
        while self.is_running:
            # First remove any perclients that have closed
            for per_client in self.per_clients:
                if not per_client.personal_thread_running:
                    print(f"{per_client}, with id {per_client.id} is no longer running, and has been pruned")
                    self.per_clients.remove(per_client)

            # Then, prescribe
            while not self.server_details.new_identities.empty():
                new_identity = self.server_details.new_identities.get()
                for per_client in self.per_clients:
                    per_client.add_prescribed_send(f"identity:{new_identity[0]} {new_identity[1]}\0") # Null terminated
            while not self.server_details.new_messages.empty():
                new_message = self.server_details.new_messages.get()
                for per_client in self.per_clients:
                    if per_client.id != new_message[0] or not DONT_ECHO:
                        per_client.add_prescribed_send(f"message:{new_message[0]} {new_message[1]}\0") # Null terminated
            
            
    def start_all_immediately(self):
        self.all_threads_running.set() # This must be set for threads to enter their infinite loop once started
        for per_client in self.per_clients:
            per_client.start()

    def join_all_immediately(self):
        self.all_threads_running.clear() # This must be cleared for threads to exit their infinite loop
        for per_client in self.per_clients:
            per_client.join()
    
#import queue
#import threading
class PerClient:
    def __init__(self, id, conn, addr, all_threads_running_event, server_details):
        self.id = id
        self.conn = conn
        self.addr = addr
        
        self.prescribed_queue = queue.Queue()
        self.all_threads_running = all_threads_running_event
        self.personal_thread_running = True
        self.server_details = server_details

        # Threads
        self.sender_thread = threading.Thread(target=self.threaded_sender, daemon=True)
        self.listener_thread = threading.Thread(target=self.threaded_listener, daemon=True)

    def start(self):
        self.sender_thread.start()
        self.listener_thread.start()

    def join(self):
        self.sender_thread.join()
        self.listener_thread.join()

    def threaded_sender(self):
        while self.all_threads_running.is_set() and self.personal_thread_running:
            current_action = self.prescribed_queue.get(block=True)
            print(f"{self.id} <--- \t{current_action}")
            self.conn.sendall(current_action.encode()) #TODO expand this, and possibly make action not a string
        
    def threaded_listener(self):
        while self.all_threads_running.is_set() and self.personal_thread_running:
            data = self.conn.recv(1024).decode()
            if data == "terminate connection": # Gracefully exit
                print(f"! User id {self.id} ({self.get_own_name()}) has requested to terminate their connection")
                self.personal_thread_running = False
                self.conn.close()
                break

                # All of the following will write to the server details
            with self.server_details.write_lock:
                if data.startswith("/nick "):
                    new_name = data[data.find(" ")+1:]
                    print(f"! User id {self.id} ({self.get_own_name()}) has requested to change their name to {new_name}")
                    self.server_details.add_identity(self.id, new_name)
                else:
                    print(f"~<{self.id} ({self.get_own_name()})> {data}")
                    self.server_details.add_message(self.id, data)

    def get_own_name(self):
        if self.id in self.server_details.persistent_identities.keys():
            return self.server_details.persistent_identities[self.id] 
        return "no name"

    def add_prescribed_send(self, action: str):
        self.prescribed_queue.put(action)

#
#
s = Server("127.0.0.1", 55000)
s.start()








