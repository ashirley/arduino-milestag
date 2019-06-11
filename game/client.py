#!/usr/bin/python

from __future__ import print_function

import argparse
import socket
import sys
import time

from player import Player
from gameLogic import GameLogic
from gameState import GameState
from clientConnection.clientConnection import ClientConnection
import proto
from core import ArgumentError


class Client():
  def __init__(self, serial = None):
    parser = argparse.ArgumentParser(description='BraidsTag gun logic.')
    parser.add_argument('-s', '--serial', type=str, help='serial device to which the arduino is connected')

    self.args = parser.parse_args()

    self.gameState = GameState(isClient=True)
    self.logic = GameLogic(self.gameState)

    if serial:
      self.serial = serial
      self.responsiveSerial = True
    else:
      if not self.args.serial:
        raise ArgumentError("You must specify -s if you do not start in fakeGun mode")

      try:
        import serial
        self.serial = serial.Serial(self.args.serial, 115200)
        self.responsiveSerial = True
      except ImportError:
        #We'll have to open this as a file
        print("WARNING: No serial module, assuming the serial argument is a normal file for testing")
        self.serial = open(self.args.serial)
        self.responsiveSerial = False
      except serial.serialutil.SerialException:
        #Try just opening this as a file
        self.serial = open(self.args.serial)
        self.responsiveSerial = False

    self.connectToArduino()

    #This blocks until a connection is established so do it after connecting to the hardware
    self.connection = ClientConnection(self, self.logic)
    self._sendToServer(proto.HELLO.create())

  def serialWrite(self, line):
    if (self.responsiveSerial):
      self.serial.write(line + "\n")

    print("-a>", repr(line + "\n"))
    sys.stdout.flush()

  def serialReadLoop(self):
    for line in self.serial:
      line = line.rstrip()
      print("<a-", repr(line))
      sys.stdout.flush()

      mainPlayer = self.gameState.getMainPlayer()

      h = proto.MessageHandler()

      @h.handles(proto.HIT)
      def hit(sentTeam, sentPlayer, damage): # pylint: disable=W0612
        self.logic.hit(time.time(), None, None, sentTeam, sentPlayer, damage)
        return True

      @h.handles(proto.FULL_AMMO)
      def fullAmmo(): # pylint: disable=W0612
        #TODO
        #self.logic.fullAmmo(self.gameState, self.player)
        return True

      @h.handles(proto.TRIGGER)
      def trigger(): # pylint: disable=W0612
        if mainPlayer:
          self.logic.trigger(time.time(), None, None)
          #TODO: What is responsible for calling this?
          #self.serialWrite(proto.FIRE.create(mainPlayer.teamID, mainPlayer.playerID, mainPlayer.gunDamage))
        return True

      #TODO be more discerning about unparseable input here.
      h.handle(line)

      if (mainPlayer):
        msg = proto.RECV.create(mainPlayer.teamID, mainPlayer.playerID, line)
      else:
        msg = proto.RECV.create(0, 0, line)
      self._sendToServer(msg)

  def _sendToServer(self, msg):
    "queue this packet to be sent to the server"
    self.connection.queueMessage(msg)

  def connectToArduino(self):
    self.serialWrite(proto.CLIENTCONNECT.create())
    line = self.serial.readline()
    print("<a-", repr(line))
    sys.stdout.flush()

    if not proto.CLIENT_CONNECTED.parse(line):
      raise RuntimeError("incorrect ack to ClientConnect(): %s" % (line))

  def shutdown(self):
    #TODO: is this the right message for this?
    self.serialWrite(proto.CLIENTCONNECT.create())

if __name__ == "__main__":
  client = Client()
  client.serialReadLoop()

  print(client.gameState.getMainPlayer())
  client.connection.stop()
  client.serial.close()
