"Test how the client handles messages from the server"

import pytest
from server import ServerGameState, ServerMsgHandler, Server
from gameEvents import GameEvent, HitEvent

# pylint:disable=redefined-outer-name

@pytest.fixture
def game_state(mocker):
    "Fixture for a gameState being tested"
    listening_thread = mocker.MagicMock()
    game_state = ServerGameState()
    game_state.setListeningThread(listening_thread)
    return game_state

@pytest.fixture
def msg_handler(mocker, game_state):
    "Fixture for a message handler being tested"
    return ServerMsgHandler(game_state.listeningThread, game_state)

@pytest.fixture
def server(mocker, msg_handler):
    "Fixture for a server which doesn't so anything with the socket and which has a mocked timeProvider"
    mocker.patch.object(Server, 'setSocket', autospec=True)

    server = Server(None, msg_handler.listeningThread, msg_handler)
    server.sock = mocker.MagicMock()
    mocker.patch.object(server, 'timeProvider', autospec=True)

    return server

def test_addHitEvent_outOfOrder(game_state, mocker):
    "Test handling of a subsequent, earlier event "
    event1 = HitEvent(100, 1, 1, 2, 1, 999)
    event2 = HitEvent(200, 2, 1, 1, 1, 999)

    game_state.getOrCreatePlayer(1, 1)
    game_state.getOrCreatePlayer(2, 1)
    game_state.startGame()

    game_state.addEvent(event2)

    assert game_state.players[(1, 1)].health > 0
    assert game_state.players[(2, 1)].health == 0

    game_state.addEvent(event1)

    assert game_state.players[(1, 1)].health == 0
    assert game_state.players[(2, 1)].health > 0

def test_detectAndHandleClockDrift(msg_handler, server, game_state, mocker):
    server.timeProvider.return_value = 300
    assert msg_handler.handleMsg("E(123def,1200,Pong(100,0))", server)
    server.timeProvider.return_value = 400
    mocker.spy(game_state, "addEvent")
    assert msg_handler.handleMsg("E(123def,1300,H2,1,3)", server)

    assert game_state.addEvent.call_count == 1
    assert game_state.addEvent.call_args[0][0].serverTime == 300
