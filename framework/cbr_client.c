/*
 *  Constant bitrate sending application
 */

#include<stdio.h>
#include<sys/socket.h>
#include<arpa/inet.h>
#include <netinet/tcp.h>
#include <sys/time.h>
#include <stdlib.h> 
#include <unistd.h>

#include "cbr_lib.h"

int main(int argc , char *argv[]) {
    const int slices_per_second = 10;
    int bitrate, bitrate_per_slice, interPacketDelay;
    int sock, i;
    int flag = 1;
    struct sockaddr_in server;
    char* req;
    char* rep;
    char* targetIp;
    int port;
    long long begin;
    int duration;
    char* scheduler;

    if(argc != 7) {
        printf("usage: cbr_client <targetIp> <port> <kb bitrate> <duration> <direction [1 == client receivs]> <scheduler>\n");
        return -1;
    }
    
    /* fill arguments */
    
    targetIp = argv[1];
    port = atoi(argv[2]);
    bitrate = atoi(argv[3]);
    duration = atoi(argv[4]);
    scheduler = argv[6];

    /* create socket */

    sock = socket(AF_INET , SOCK_STREAM , 0);

    if (sock == -1) {
        printf( "Could not create socket");
        return -1;
    }

    server.sin_addr.s_addr = inet_addr(targetIp);
    server.sin_family = AF_INET;
    server.sin_port = htons( port );

    /* connect */

    if (connect(sock , (struct sockaddr *)&server , sizeof(server)) < 0) {
        perror("connect failed. Error");
        return 1;
    }

    

    if(atoi(argv[5]) == 0) {
        sleep(1);
        setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, (char *) &flag, sizeof(int));
        run_sender(sock, bitrate, duration);
    } else if(atoi(argv[5]) == 1) {
        run_receiver(sock, bitrate, duration);
    } else {
        printf("Unexpected direction...");
    }
    return 0;
}
