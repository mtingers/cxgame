"""
Example of running a feed and exchange server at the same time.
"""
import threading
from cxgame.server import CxServer, CxFeed, CxExchange

def main():
    """Simplest example of starting the servers."""
    server = server.CxServer(time_limit=300) # Shuts down after 5 minutes
    server.start()

def manually_run_server_threads():
    """This example shows how to manually start each server. It is what
    CxServer does under the hood.
    """
    feed_server = server.CxFeed()
    exc_server = server.CxExchange(time_limit=300) # Shuts down after 5 minutes
    th1 = threading.Thread(target=feed_server.start)
    th2 = threading.Thread(target=exc_server.start)
    th1.start()
    th2.start()
    for t in (th1, th2):
        t.join()

if __name__ == '__main__':
    main()
