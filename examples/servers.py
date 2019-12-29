"""
Example of running a feed and exchange server at the same time.
Note that the feed server must be run in the same process as the exchange
server since they share the global STATE variable. It is currently not possible
to run CxFeed in a separate process.
"""
import threading
from cxgame import server

def main():
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
