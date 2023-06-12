/****************************************************************************

 i106_decode_uart.c

 ****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libirig106.h"
#include "i106_util.h"

#include "i106_uart.h"


/* Function Declaration */

static void FillInMessagePointers(UARTF0_Message *msg);


I106Status I106_Decode_FirstUARTF0(I106C10Header *header, void *buffer,
        UARTF0_Message *msg){

    // Keep a pointer to the current header    
    msg->Header = header;

    msg->BytesRead = 0;

    // Set pointers to the beginning of the UART buffer
    msg->CSDW = (UARTF0_CSDW *)buffer;

    msg->BytesRead += sizeof(UARTF0_CSDW);

    return I106_Decode_NextUARTF0(msg);
}


I106Status I106_Decode_NextUARTF0(UARTF0_Message *msg){
    
    // Check for no more data
    if (msg->Header->DataLength <= msg->BytesRead)
        return I106_NO_MORE_DATA;

    // Get the other pointers
    FillInMessagePointers(msg);

    FillInTimeStruct(msg->Header, msg->IPTS, &msg->Time);

    return I106_OK;
}


void FillInMessagePointers(UARTF0_Message *msg){

     // Set the pointer to the intra-packet time stamp if available
    if(msg->CSDW->IPH){
        msg->IPTS = (IntraPacketTS *)((char *)(msg->CSDW) + msg->BytesRead);
        msg->BytesRead += sizeof(msg->IPTS->IPTS);
    }
    else
        msg->IPTS = NULL;

    // Set the pointer to the intra-packet header
    msg->IPH = (UARTF0_IPH *)((char *)(msg->CSDW) + msg->BytesRead); 
    msg->BytesRead += sizeof(UARTF0_IPH);
    
    // Set the pointer to the data
    msg->Data = (uint8_t *)((char *)(msg->CSDW) + msg->BytesRead);

    // Add the data length, if it is odd, account for the filler byte we will skip   
    msg->BytesRead += msg->IPH->Length + (msg->IPH->Length % 2);    
}
