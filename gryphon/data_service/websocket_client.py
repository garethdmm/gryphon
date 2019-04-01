from autobahn.twisted.websocket import WebSocketClientProtocol
from twisted.internet import reactor
from twisted.python import log


class EmeraldWebSocketClientProtocol(WebSocketClientProtocol):
    def onConnect(self, response):
        log.msg("Web Socket Server connected: {0}".format(response.peer))

    def onOpen(self):
        raise NotImplementedError

    def onMessage(self, payload, isBinary):
        raise NotImplementedError

    def onClose(self, wasClean, code, reason):
        log.msg(
            "WebSocket connection closed: %s : Code %s : wasClean:%s. Restarting." % (
            reason,
            code,
            wasClean,
        ))

        reactor.callLater(2, self.start)
