# -*- coding: utf-8 -*-

import calendar
import collections
import ctypes
import datetime
import os
import sys
import time

import Py106
import Py106.MsgDecode1553

import tables
import numpy


#class Index1553Msg(tables.IsDescription):
#    ''' Class to hold index information 
#        msg_index - Array index of message
#        msg_time  - UTC time of indexed message
#    '''
#    msg_index = tables.Int64Col()
#    msg_time  = tables.Time64Col()


# Class to handle 1553 data types
# ===============================
class Msg1553(object):
    def __init__(self, layout_version = 1):
        self.layout_version = layout_version
        self.msg_time     = Py106.Time.IrigTime()
        self.chan_id      = numpy.uint16(0)
        self.header_flags = numpy.uint16(0)
        self.cmd_word_1   = numpy.uint16(0)
        self.stat_word_1  = numpy.uint16(0)
        self.cmd_word_2   = numpy.uint16(0)
        self.stat_word_2  = numpy.uint16(0)
        self.data         = []
    
    def encode_tuple(self):
        if self.layout_version == 1:
            time_secs  = calendar.timegm(self.msg_time.time.timetuple())
            time_fracs = self.msg_time.time.microsecond
            time_fmt   = self.msg_time.dt_format
            flags_p    = ctypes.pointer(self.header_flags)
            flags_ip   = ctypes.cast(flags_p, ctypes.POINTER(ctypes.c_uint16))
            if flags_ip[0] == 48068:
                pass
            return \
                (time_secs,                       \
                 time_fracs,                      \
                 numpy.uint8(time_fmt),           \
                 numpy.uint16(self.chan_id),      \
                 numpy.uint16(flags_ip[0]), \
                 numpy.uint16(self.cmd_word_1),   \
                 numpy.uint16(self.stat_word_1),  \
                 numpy.uint16(self.cmd_word_2),   \
                 numpy.uint16(self.stat_word_2),  \
                 self.data)
        else:
            return


    def decode_tuple(self, msg_tuple):
        '''Decode a 1553 information atuple and fill in our class data'''
        if self.layout_version == 1:
            self.msg_time = Py106.Time.IrigTime()
            self.msg_time.time = datetime.datetime.utcfromtimestamp(msg_tuple[0]) 
            self.msg_time.time = self.msg_time.time.replace(microsecond=msg_tuple[1])
            self.msg_time.dt_format = msg_tuple[2]

            self.chan_id     = msg_tuple[3]
            
            self.header_flags = Py106.MsgDecode1553.Hdr1553_Flags()
            flags_p          = ctypes.pointer(self.header_flags)
            flags_ip         = ctypes.cast(flags_p, ctypes.POINTER(ctypes.c_uint16))
            flags_ip[0]      = msg_tuple[4]

            self.cmd_word_1  = Py106.MsgDecode1553.CmdWord(msg_tuple[5])
            self.stat_word_1 = Py106.MsgDecode1553.StatWord(msg_tuple[6])
            self.cmd_word_2  = Py106.MsgDecode1553.CmdWord(msg_tuple[7])
            self.stat_word_2 = Py106.MsgDecode1553.StatWord(msg_tuple[8])
            self.data        = msg_tuple[9]
        else:
            return


# Class for getting IRIG data into a PyTables table
# =================================================

class H5Table(object):
    ''' Store and manipulate IRIG 106 data as a PyTables table '''

    
    # H5Table methods
    # ---------------
    
    def __init__(self):
        self.ch10_file = None
        
    def __del__(self):
        if self.ch10_file != None:
            self.ch10_file.close()
        
    def ImportOpen(self, irig_filename, hdf5_filename="", force=False):
        ''' Open a Ch 10 file and read it into a PyTables table or open
            an existing (i.e. already converted) table.
            Return the PyTable table file object
        '''

        # Make the HDF5 file name
        if hdf5_filename == "" :
            (hdf5_filename, ext) = os.path.splitext(irig_filename)
            hdf5_filename += ".h5"

        # Try opening an existing HDF5 file
        if force == False:
            try:
                self.ch10_file = tables.openFile(hdf5_filename, mode = "r")
            except Exception as e:
                pass
            else:
                return self.ch10_file

        # Make IRIG 106 library classes
        self.pkt_io     = Py106.Packet.IO()
        self.time_utils = Py106.Time.Time(self.pkt_io)
        self.decode1553 = Py106.MsgDecode1553.Decode1553F1(self.pkt_io)
    
        # Initialize variables
        packet_count      = 0
        packet_count_1553 = 0
        msg_count_1553    = 0
    
        # Open the IRIG file
        ret_status = self.pkt_io.open(irig_filename, Py106.Packet.FileMode.READ)
        if ret_status != Py106.Status.OK :
            print "Error opening data file %s" % (irig_filename)
            sys.exit(1)

        ret_status = self.time_utils.SyncTime(False, 10)
#        if ret_status != Py106.Status.OK:
#            print ("Sync Status = %s" % Py106.Status.Message(ret_status))
#            sys.exit(1)
        
        # Open the PyTable tables
        self.ch10_file      = tables.openFile(hdf5_filename, mode = "w", title = "Ch 10 Data File")
#        ch10_bus_data_group = self.ch10_file.createGroup("/", "Bus_Data_Group")
        ch10_bus_data       = self.ch10_file.createVLArray("/", "Bus_Data", tables.ObjectAtom(), title="1553 Bus Data")
        ch10_bus_data.attrs.layout_version = 1
 #       ch10_bus_data_index = self.ch10_file.createTable("/", "Bus_Data_Index", Index1553Msg, "1553 Bus Data Time Index")

        # Important note: for pickle to work the classname MUST match the typename 
#        msg_tuple = collections.namedtuple('msg_tuple', "Time ChanID CmdWord1 StatWord1 CmdWord2 StatWord2 Data")
            
        for PktHdr in self.pkt_io.packet_headers():
            packet_count += 1
#            print str.format("Packet Time 0x{0:02x}{1:02x}{2:02x}{3:02x}{4:02x}{5:02x}", \
#                self.pkt_io.Header.RefTime[5],self.pkt_io.Header.RefTime[4],\
#                self.pkt_io.Header.RefTime[3],self.pkt_io.Header.RefTime[2],\
#                self.pkt_io.Header.RefTime[1],self.pkt_io.Header.RefTime[0])

            if PktHdr.DataType == Py106.Packet.DataType.IRIG_TIME:
#                print "Time Packet"
                pass

            if PktHdr.DataType == Py106.Packet.DataType.MIL1553_FMT_1:
#                print "1553 Packet"

                packet_count_1553 += 1
                self.pkt_io.read_data()
                for Msg in self.decode1553.msgs():
                    msg_count_1553 += 1

#                    print str.format("Msg Time 0x{0:012x}", Msg.p1553Hdr.contents.Field.PktTime)

                    # Extract the import 1553 info
                    WC = self.decode1553.word_cnt(Msg.pCmdWord1.contents.Value)

                    # Put the 1553 message data into our storage class
                    msg_1553              = Msg1553()
                    msg_1553.msg_time     = self.time_utils.RelInt2IrigTime(Msg.p1553Hdr.contents.Field.PktTime)
                    msg_1553.chan_id      = numpy.uint16(self.pkt_io.Header.ChID)
                    msg_1553.header_flags = Msg.p1553Hdr.contents.Field.Flags
                    msg_1553.cmd_word_1   = numpy.uint16(Msg.pCmdWord1.contents.Value)
                    msg_1553.stat_word_1  = numpy.uint16(Msg.pStatWord1.contents.Value)
                    if (Msg.p1553Hdr.contents.Field.Flags.RT2RT == 0):
                        msg_1553.cmd_word_2  = numpy.uint16(0)
                        msg_1553.stat_word_2 = numpy.uint16(0)
                    else:
                        msg_1553.cmd_word_2  = numpy.uint16(Msg.pCmdWord2.contents.Value)
                        msg_1553.stat_word_2 = numpy.uint16(Msg.pStatWord2.contents.Value)
                    msg_1553.data = numpy.array(Msg.pData.contents[0:WC])
                    msg_1553.layout_version = ch10_bus_data.attrs.layout_version
                    DataMsg = msg_1553.encode_tuple()

#                    if   (Msg.p1553Hdr.contents.Field.Flags.RT2RT       ==        0) and \
#                         (Msg.p1553Hdr.contents.Field.Flags.RespTimeout ==        0) and \
#                         (Msg.p1553Hdr.contents.Field.MsgLen            == (WC*2+4)):
#                        print str.format("BC/RT - {0} {1}  WC={2}, DataLen={3}", \
#                            msg_1553.chan_id, Msg.pCmdWord1.contents, \
#                            WC, Msg.p1553Hdr.contents.Field.MsgLen)
#                        pass
#                    elif (Msg.p1553Hdr.contents.Field.Flags.RT2RT       ==        0) and \
#                         (Msg.p1553Hdr.contents.Field.Flags.RespTimeout ==        1) and \
#                         (Msg.p1553Hdr.contents.Field.MsgLen            == (WC*2+2)):
#                        print str.format("BC/RT No Resp - {0} {1}  WC={2}, DataLen={3}", \
#                            msg_1553.chan_id, Msg.pCmdWord1.contents, \
#                            WC, Msg.p1553Hdr.contents.Field.MsgLen)
#                        pass
#                    elif (Msg.p1553Hdr.contents.Field.Flags.RT2RT == 1       ) and \
#                         (Msg.p1553Hdr.contents.Field.MsgLen      == (WC*2+8)):
#                        print str.format("RT/RT - {0} {1}  WC={2}, DataLen={3}", \
#                            msg_1553.chan_id, Msg.pCmdWord1.contents, \
#                            WC, Msg.p1553Hdr.contents.Field.MsgLen)
#                        pass
#                    elif Msg.p1553Hdr.contents.Field.Flags.WordCntError == 1:
#                        print "Word Count Error Flag"
#                        pass
#                    else:
#                        print str.format("Word Count Error - {0} {1}  WC={2}, DataLen={3}", \
#                            msg_1553.chan_id, Msg.pCmdWord1.contents, \
#                            WC, Msg.p1553Hdr.contents.Field.MsgLen)
#                        pass
                    
                    ch10_bus_data.append(DataMsg)

                    # Store the 1553 data time index
#                    msg_index = ch10_bus_data_index.row
#                    msg_index['msg_index'] = ch10_bus_data.nrows - 1
#                    time_tuple_utc = msg_time.time.timetuple()
#                    timestamp_utc  = calendar.timegm(time_tuple_utc)
#                    timestamp_utc += msg_time.time.microsecond / 1000000.0
#                    msg_index['msg_time']  = timestamp_utc
#                    msg_index.append()

                    # Print the 1553 info
                    if False:
                        sys.stdout.write ("%s Ch %3i %s " % (msg_1553.msg_time, self.pkt_io.Header.ChID, Msg.pCmdWord1.contents))
                        if Msg.p1553Hdr.contents.MsgError == 0:
                            for iDataIdx in range(WC):
#                               sys.stdout.write("%04x " % Msg.pData.contents[iDataIdx])
                                sys.stdout.write("%i " % Msg.pData.contents[iDataIdx])
                        else:
                            sys.stdout.write("Msg Error")
                        print
    
                # Done with 1553 messages in packet

        print "Packets       = %d" % packet_count
        print "1553 Packets  = %d" % packet_count_1553
        print "1553 Messages = %d" % msg_count_1553

        self.ch10_file.flush()
        self.pkt_io.close()
        
        return self.ch10_file
        
        

# ---------------------------------------------------------------------------
# Module initialization
# ---------------------------------------------------------------------------

msg_tuple = collections.namedtuple('msg_tuple', "Time ChanID CmdWord1 StatWord1 CmdWord2 StatWord2 Data")



# This test code just opens an IRIG file and does a histogram of the 
# data types
    
if __name__=='__main__':
    print "IRIG 1106 Decode 1553"

    irig_table = H5Table()
    
    if len(sys.argv) > 1 :
        msg_1553_file = irig_table.ImportOpen(sys.argv[1], force=False
        )
    else :
        print "Usage : HDF5Test.py <filename>"
        sys.exit(1)

#    print msg_1553_file
 
    # Get a reference to the 1553 bus data table
    bus_data =  msg_1553_file.root.Bus_Data

    # Get the layout version of the 1553 data
    layout_version = bus_data.attrs.layout_version

    # Get a slice of data out of the middle
    start = bus_data.nrows / 2
    stop  = start + 100
    msg_slice = msg_1553_file.root.Bus_Data[start:stop]
    msg_read = Msg1553()
    
    # Just for fun print out some data
    for idx in range(100):
        msg_read.layout_version = layout_version
        msg_read.decode_tuple(msg_slice[idx])
        print str.format("{0} Chan ID {1} {2}", msg_read.msg_time, msg_read.chan_id, msg_read.cmd_word_1)
        
    pass

    msg_read = None