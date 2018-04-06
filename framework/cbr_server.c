/*
 *   Constant bitrate receiving application
 */

#include<stdio.h>
#include<string.h>    //strlen
#include<sys/socket.h>
#include<arpa/inet.h> //inet_addr
#include<unistd.h>    //write
#include<netinet/tcp.h>
#include <stdlib.h>
#include <sys/time.h>
#include <errno.h>

#include "cbr_lib.h"

int main(int argc , char *argv[])
{
    int msg_size = 8096;
    int socket_desc , client_sock , c , read_size;
    struct sockaddr_in server , client;
    char* msg = (char*) malloc(sizeof(char) * msg_size);
    int flag = 1;
    int i;
    int maxI;
    int port;

    long long begin;
    long long tmp;
    int duration;
    int bitrate;

    if(argc != 5) {
        printf("usage: cbr_server <port> <kb bitrate> <duration> <direction>\n");
        return -1;
    }
    
    /* fill arguments */
    
    port = atoi(argv[1]);
    bitrate = atoi(argv[2]);
    duration = atoi(argv[3]);

    /* create socket */
    
    socket_desc = socket(AF_INET , SOCK_STREAM , 0);
    if (socket_desc == -1) {
        printf("Could not create socket");
        return -1;
    }

    server.sin_family = AF_INET;
    server.sin_addr.s_addr = INADDR_ANY;
    server.sin_port = htons( port );

    if( bind(socket_desc,(struct sockaddr *)&server , sizeof(server)) < 0) {
        printf("bind failed. Error");
        return 1;
    }

    if( listen(socket_desc , 5) < 0) {
        printf("listen failed. Error");
        return 1;
    }

    /* wait for connection */
    
    //printf("Waiting for incoming connections...\n");
    fflush(stdout);
    int erbefore = errno;
    
    client_sock = accept(socket_desc, (struct sockaddr *)&client, (socklen_t*)&c);
    if (client_sock < 0) {
        printf("accept failed %i with error %i before %i\n", client_sock, errno, erbefore);
        return 1;
    }
    
    if(atoi(argv[4]) == 0) {
        run_receiver(client_sock, bitrate, duration, -1);
    } else if(atoi(argv[4]) == 1) {
        //printf("Connection accepted\n");
        /* be sure it is mptcp */
        sleep(1);
        setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, (char *) &flag, sizeof(int));
   
        run_sender(client_sock, bitrate, duration);
    } else {
        printf("Unexpected direction...");
    }
    
    /* clean up */
    close(socket_desc);

    printf("finished");
    return 0;
}
