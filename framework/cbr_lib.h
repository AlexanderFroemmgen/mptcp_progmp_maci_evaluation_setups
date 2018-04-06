/*
 *  Constant bitrate lib
 */

#include<stdio.h>
#include<sys/socket.h>
#include<arpa/inet.h>
#include <netinet/tcp.h>
#include <sys/time.h>
#include <stdlib.h> 
#include <unistd.h>

long long current_time_ms() {
    struct timeval te; 
    gettimeofday(&te, NULL);
    long long milliseconds = te.tv_sec*1000LL + te.tv_usec/1000;
    return milliseconds;
}

struct rbs_rule_value {

  unsigned int reg_num;

  unsigned int value;

};

int rbs_set_reg(int sock, unsigned int reg_num, unsigned int value) {
  struct rbs_rule_value val;
  val.reg_num = reg_num;
  val.value = value;

  return !setsockopt(sock, IPPROTO_TCP, 45, &val, sizeof(struct rbs_rule_value));
}

void set_kb_rate(int sock, int rate) {
	printf("setting rate to %i results in %i\n", rate, rbs_set_reg(sock, 0, rate));
	fflush(stdout);
}

void run_sender(int sock, int bitrate, int duration) {
    const int slices_per_second = 10;
    int bitrate_per_slice, interPacketDelay;
    int i;
    char* req;
    char* rep;
    long long begin;

    interPacketDelay = 1000 % bitrate;
    bitrate_per_slice = bitrate / slices_per_second;

    /* prepare data */
    
    req = (char*) malloc(1024);
    rep = (char*) malloc(1024);

    for(i=0;i<1024;i++) {
        req[i]=0x41;
    }

    begin = current_time_ms();

    set_kb_rate(sock, bitrate);
    
    for(i=0;i < duration * slices_per_second;i++) {
        long long tmp = current_time_ms();
        
        //printf("%3i: sending %i kb at time %10lli in time %10lli\n", i, bitrate_per_slice, tmp, (tmp - begin));
       
        for(int j =0;j<bitrate_per_slice;j++) {
            if( send(sock , req , 1024 , 0) < 0) {
                printf( "Send failed");
                return;
            }
        }

/*	if(i == 6 * slices_per_second) {
		// 4 times after 6 seconds
		bitrate_per_slice *= 4;
		bitrate *= 4;
		set_kb_rate(sock, bitrate);
	}*/

        /* wait till slice is finished */
        while(1) {
            if(begin + 1000 * (i + 1) / slices_per_second < current_time_ms()) {
                break;
            }
        }
    }

    printf("finished but wait");
    fflush(stdout);
     /* wait two more seconds */
    sleep(2);

    /* clean up */
    
    fflush(stdout);
    close(sock);
}

void run_receiver(int sock, int bitrate, int duration, int incTime) {
    int msg_size = 8096;
    int read_size;
    char* msg = (char*) malloc(sizeof(char) * msg_size);
    int i;
    long long begin;

    for(i=0;i < duration;i++) {
        read_size = 0;
        long long begin = current_time_ms();
        
        while(1) {
            int tmpSize = recv(sock , msg , msg_size , 0);

            if(tmpSize > 0) {
                read_size += tmpSize;
            }
            
            if(read_size > bitrate * 1000) {
                /* print the time it took to read what was expected to be 1000 ms */
                printf("%lli\n", (current_time_ms() - begin));
                fflush(stdout);
                break;
            }
        }

	if(i == incTime) { /* e.g. 6 */
		bitrate *= 4;
		printf("new bitrate is %u\n", bitrate);
	}
    }

    if(read_size == 0) {
        printf("Client disconnected");
        fflush(stdout);
    } else if(read_size == -1) {
        printf("recv failed");
    }
    
    /* clean up */
    
    close(sock);
    //fflush(stdout);
}
