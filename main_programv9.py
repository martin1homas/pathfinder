#Import modules for # DB
#import xml.etree.ElementTree as ET
import sqlite3
import re
import os
import sys
from sqlite3 import Error
import logging
from numpy import array
import numpy as np
import ast


#Collect source and destination
sourceip=''
destinationip=''
#List of Device configurations and device_type

####Funtions for octect and mask manipulations##########

# Python code to convert decimal to binary
# function definition
# it accepts a decimal value
# and prints the binary value
def decToBin(dec_value):
    # logic to convert decimal to binary
    # using recursion
    bin_value =''
    q=int(dec_value)
    while (q > 1):
        r=q % 2
        q=q //2
        bin_value= str(r) + bin_value

    r=q % 2
    bin_value= str(r) + bin_value
    return bin_value
#counts how many 1s in a bynary
def countMaskBit(bin):
    #counts how many 1s in a bynary mask from left to right
    lenght=len(bin)
    x=0
    count=0
    while (x < lenght):
        count=int(bin[x])+count
        x=x+1
    return count

def octectmask2bitlenmask(mask):
    #i.e 255.255.255.0  ----> /24
    mask1=octect2bin(mask)
    return str(countMaskBit(mask1))
def bitlenmask2obtectmask(mask):
    #i.e /24 ----> 255.255.255.0
    mask1=masklen2maskbin(mask)
    mask2=binIP2octect(mask1)
    return mask2
def octect2bin(mask):
# for a 255.0.0.0  will return 11111111000000000000000000000000 and so on
    bytelist=mask.split('.')
   
    binary=''
    for byte in bytelist:
        newbin=decToBin(byte)
        l=len(newbin)
        if l<8:
            i=8-l
            while i>0:
                newbin='0'+newbin
                i=i-1
            binary=binary+newbin
        else:
            binary=binary+newbin
    return binary
def masklen2maskbin(mask):
    #Transforms a  /24 in 11111111.11111111.11111111.00000000
    bit=0
    mask=int(mask)
    byte=''
    while bit<32:
        
        if bit<mask:
            byte=byte+'1'
            
        if mask<=bit:
            byte=byte+'0'
            
        bit=bit+1
    return(byte)

def binIP2octect(bin_IPv4):
    #Does the reverse as octect2bin, note that is not checking the range of the octects
    # for a  11111111000000000000000000000000  will return 255.0.0.0  and so on
        a=0
        b=0
        c=0
        d=0
        i=0
        if (len(bin_IPv4)!=32):
            print('bad octect lenght')

        else:
            while (i<8):
                a=a+int(bin_IPv4[i])*pow(2,7-i)
                b=b+int(bin_IPv4[i+8])*pow(2, 7-i)
                c=c+int(bin_IPv4[i+16])*pow(2, 7-i)
                d=d+int(bin_IPv4[i+24])*pow(2, 7-i)
                i=i+1
        octect=(str(a)+'.'+str(b)+'.'+str(c)+'.'+str(d))
        return octect
def host2subnet(ip,mask):
    #Given a host in octect and mask in octect format, returns subnet in octect and mask lenght
    maskbin=octect2bin(mask)
    ipbin=octect2bin(ip)
    len=countMaskBit(maskbin)
    subnet=''
    i=0
    while i<32:
        if i<len:
            subnet=subnet+ipbin[i]
        else:
            subnet=subnet+'0'
        i=i+1
    subnet=binIP2octect(subnet)
    returntuple=(subnet,mask)
    return returntuple

def if_in_net(host_octect, subnet_octect, subnet_mask_bitlen):
    #host/subnet in octect format, masks in mask lenght format. i.e ('10.2.34.5','10.2.34.0','/24')
    subnet_mask_octect=bitlenmask2obtectmask(subnet_mask_bitlen)
    print(subnet_mask_octect)
    print(type(subnet_mask_octect))
    
    (host_subnet,host_mask)=host2subnet(host_octect,subnet_mask_octect)
    
    print(host_subnet)
    print(type(host_subnet))
    if host_subnet == subnet_octect:
        return True
    else:
        return False
    
#########Functions for extraction of information from configuration #########

def extract_route_static(device,config,device_type,routedomain):
    #re imported in main program
    #This function assumes that the device is in the table Devices
    #This will return always a tuple like: (subnet[0],mask[0],nexthop[0],device)
    fh=open(config)
    print('Reading static routes from: '+device_type+' '+device+'\n')
    administrative_distance=1
    if device_type=='ASA':
        #Code for ASA follows
            for line in fh:
                if line.startswith('hostname'):
                    x=line.split()
                    
                if line.startswith('route'):
                    x=line.split()
                    IPs= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    subnet=IPs[0]
                    mask=IPs[1]
                    if len(IPs)<3:
                        #In same cases the route nexthop is not an IP but a name , for
                        #Instance:route INTERFACE_NAME SUBNET_IP MASK_IP NAME_IP 1
                        #Where NAME_IN_CONFIG will defined in config: name IP NAME_IP
                        #In this cases the line route len will < 3, and it and nexthop missing
                        #To find the IP of NAME_IP
                        nfh=open(config)
                        for line2 in nfh:
                            #Looking for the NAME_IP to add NEXT_HOP
                            if line2.startswith('name '):
                                
                                IP_NAME=re.findall('name\s[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+\s(.+)',line2)
                                y=line2.split()
                                
                                if IP_NAME[0]==x[4]:
                                    
                                    nexthop=y[1]
                                    

                    else:
                        nexthop=IPs[2]

                    maskbin=octect2bin(mask)
                    mask=countMaskBit(maskbin)
                    add_route(subnet,mask,nexthop,administrative_distance,device)
                    #route=(subnet,mask,nexthop)
                else:
                    continue
        #Insert in the database
    if device_type=='JUNIPER':
        #Code for Juniper follows
        for line in fh:
            if line.startswith('set routing-options static route'):
                x=line.split()
                if x[4]=='<REMOVED>':
                    continue
                subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[/]',x[4])
                mask=re.findall('/([0-9]+)',x[4])
                nexthop=x[6]
                
                #route=(subnet[0],mask[0],nexthop)
                add_route(subnet[0],mask[0],nexthop,administrative_distance,device)

    if device_type=='F5':
        #Code for F5 follows
        #Inizialize counter
        counter=0
        for line in fh:
            if counter==2:
                x=line.split()
                #Chose route depending on route domain in F5
                if routedomain=='default':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)/',x[1])
                    mask=re.findall('[.][0-9]+/([0-9]+)',x[1])
                    if re.search('default$',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']

                if routedomain=='1':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%1',x[1])
                    mask=re.findall('%1/([0-9]+)',x[1])
                    if re.search('default\%1',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='2':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%2',x[1])
                    mask=re.findall('%2/([0-9]+)',x[1])
                    if re.search('default\%2',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='3':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%3',x[1])
                    mask=re.findall('%3/([0-9]+)',x[1])
                    if re.search('default\%3',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='4':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%4',x[1])
                    mask=re.findall('%4/([0-9]+)',x[1])
                    if re.search('default\%4',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='5':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%5',x[1])
                    mask=re.findall('%5/([0-9]+)',x[1])
                    if re.search('default\%5',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if routedomain=='6':
                    subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%6',x[1])
                    mask=re.findall('%6/([0-9]+)',x[1])
                    if re.search('default\%6',x[1]):
                        subnet=['0.0.0.0']
                        mask=['0']
                if len(subnet)>>0:
                    #subnet and mask are type lst
                    route=(subnet[0],mask[0],nexthop[0])
                    add_route(subnet[0],mask[0],nexthop[0],administrative_distance,device)
                    subnet=[]
                    mask=[]

                counter=0
            if counter==1:
                #nexthop are type string
                x=line.split()
                nexthop=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)',x[1])
                counter=2
            if line.startswith('net route '):
                    counter=1
                    
            else:
                continue
    if device_type=='Cisco_IOS':
        #Code for Cisco IOS follows
            for line in fh:
                if line.startswith('ip route'):
                    #Searching for this pattern 'ip route 10.159.92.6 255.255.255.255 10.158.0.89'
                    x=line.split()
                    IPs= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)

                    if len(IPs)<3:
                        #In same cases the route nexthop is not an IP but an interface ,so need to add interface
                        nexthop=(x[4])
                    else:
                        nexthop=IPs[2]

                    mask=IPs[1]
                    subnet=IPs[0]
                    maskbin=octect2bin(mask)
                    mask=countMaskBit(maskbin)
                    #Insert in the database
                    add_route(subnet,mask,nexthop,administrative_distance,device)
                    #route=(subnet,mask,nexthop,device)

def extract_route_connected(device,config,device_type,routedomain):
    administrative_distance=0
    fh=open(config)
    print('Reading connected routes from: '+device_type+' '+device+'\n')
    if device_type=='ASA':
    #Code for ASA follows
    #How an engineer does it, it looks at the configuration, looking for interface commands, then under
    #the command, it looks for ip address  and mask, and also for ip address and mask secondary.
    #After that it just calculates the subnets for each ip,mask
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        Intlst=list()
        for line in fh:
            if line.startswith('interface'):
                inside_int=True
                enabled_int=True
                interface=re.findall('interface (\S+)',line)
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    #Mask=octectmask2bitlenmask(Address[1])
                    Mask=Address[1]
                    Int=interface[0]
                    Addlst.append(IP)
                    Masklst.append(Mask)
                    Intlst.append(Int)

                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        while i<x:
                            subnettuple=host2subnet(Addlst[i],Masklst[i])
                            add_route(subnettuple[0],subnettuple[1],Intlst[0],administrative_distance,device)

                            i=i+1
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()
                        Intlst=list()    
    if device_type=='JUNIPER':
        #Code for Juniper follows
        for line in fh:
            if line.startswith('set interfaces '):
                
                x=line.split()
                subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[/]',line)
                if len(subnet)>0:
                    mask=re.findall('/([0-9]+)',line)
                    interface=x[2]+' '+x[3]+' '+x[4]
                    
                    maskbin=masklen2maskbin(mask[0])
                    mask=binIP2octect(maskbin)
                    subnettuple=host2subnet(subnet[0],mask)
                    
                    mask1=octectmask2bitlenmask(mask)
                    #add_route(subnettuple[0],subnettuple[1],interface,administrative_distance,device)
                    add_route(subnettuple[0],mask1,interface,administrative_distance,device)
                    subnet=''
                else:
                    continue

    if device_type=='F5':
        inside_int=False
        enabled_int=True
        for line in fh:
            if line.startswith('net self'):
                interface=re.findall('/Common/(\S+)',line)
                inside_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith('    address'):
                    if routedomain=='default':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)/',line)
                        mask=re.findall('[.][0-9]+/([0-9]+)',line)

                    if routedomain=='1':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%1/',line)
                        mask=re.findall('[.][0-9]+%1/([0-9]+)',line)

                    if routedomain=='2':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%2/',line)
                        mask=re.findall('[.][0-9]+%2/([0-9]+)',line)

                    if routedomain=='3':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%3/',line)
                        mask=re.findall('[.][0-9]+%3/([0-9]+)',line)

                    if routedomain=='4':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%4/',line)
                        mask=re.findall('[.][0-9]+%4/([0-9]+)',line)

                    if routedomain=='5':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%5/',line)
                        mask=re.findall('[.][0-9]+%5/([0-9]+)',line)

                    if routedomain=='6':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%6/',line)
                        mask=re.findall('[.][0-9]+%6/([0-9]+)',line)

                if ((inside_int==True) and line.startswith('}')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if len(subnet)>>0:
                        maskbin=masklen2maskbin(mask[0])
                        maskoct=binIP2octect(maskbin)
                        maskoct1=octectmask2bitlenmask(maskoct)
                        subnettuple=host2subnet(subnet[0],maskoct)
                        
                        add_route(subnettuple[0],maskoct1,interface[0],administrative_distance,device)
                        subnet=[]
                        mask=[]
                        interface=[]
                    else:
                        continue

    if device_type=='Cisco_IOS':
        #Code for ASA follows
        #How an engineer does it, it looks at the configuration, looking for interface commands, then under
        #the command, it looks for ip address  and mask, and also for ip address and mask secondary.
        #After that it just calculates the subnets for each ip,mask
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        for line in fh:
            if line.startswith('interface'):
                line_interface=line.split()
                interface=line_interface[1]
                inside_int=True
                enabled_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    Mask=Address[1]
                    Addlst.append(IP)
                    Masklst.append(Mask)

                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        while i<x:
                            subnet=host2subnet(Addlst[i],Masklst[i])
                            mask1=octectmask2bitlenmask(subnet[1])
                            add_route(subnet[0],mask1,interface,administrative_distance,device)
                            i=i+1
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()

def extract_interface(device,config,device_type,routedomain):
    #administrative_distance=0
    fh=open(config)
    print('Reading interfaces from: '+device_type+' '+device+'\n')
    if device_type=='ASA':
    #Code for ASA follows
    #How an engineer does it, it looks at the configuration, looking for interface commands, if it finds it
    #records the interface name, then under the interface , it looks for ip address  and mask,
    # and also for ip address and mask secondary.in the case of
    #ASA the name if, zone, 
        inside_int=False
        enabled_int=True
        Addlst=list()
        IPlst=list()
        Masklst=list()
        Intlst=list()
        zone=''
        for line in fh:
            if line.startswith('interface'):
                inside_int=True
                enabled_int=True
                interface=re.findall('interface (\S+)',line)
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    Mask=octectmask2bitlenmask(Address[1])
                    Int=interface[0]
                    Addlst.append(IP)
                    Masklst.append(Mask)
                    Intlst.append(Int)
                    ip_address=''
                    ip_mask=''
                if line.startswith(' nameif'):
                    zoneline=line.split()
                    nameif=zoneline[1]
                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        i=0
                        address=''
                        if x>0:
                            while i<x:
                                if i==0:
                                    #This is if is required to avoid an space in front of the interface_ip
                                    #that ends up making fail the queries for who_has(ip) function for ASA
                                    ip_address= ip_address+Addlst[i]
                                    ip_mask= ip_mask+' '+Masklst[i]
                                else:
                                    ip_address= ip_address+' '+Addlst[i]
                                    ip_mask= ip_mask+' '+Masklst[i]
                                i=i+1
                                add_interface(interface[0],device,ip_address,ip_mask,nameif,zone)
                        Addlst=list()
                        IPlst=list()
                        Masklst=list()
                        Intlst=list()
                        address=''
    if device_type=='JUNIPER':
        #Code for Juniper follows
        add_interface_arguments=list()
        interface_zone_and_names=list()
        for line in fh:
            if line.startswith('set interfaces '):
                x=line.split()
                subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[/]',line)
                if len(subnet)>0:
                    mask=re.findall('/([0-9]+)',line)
                    interface=x[2]+'.'+x[4]
                    maskbin=masklen2maskbin(mask[0])
                    nameif='n/a'
                    zone='n/a'
                    add_interface_arguments.append([interface,device,subnet[0],mask[0],nameif,zone])
                    #Zone will be added latter on
                    #GigabitEthernet0/7 572118  10.159.0.1  25 nameif,zone
            if line.startswith('set security zones security-zone'):
                x=line.split()
                
                #Select this kind of lines only: set security zones security-zone FW_BACKEND_SRV interfaces reth1.300
                if (len(x)>6) and (x[5]=='interfaces'):
                    interface_zone_and_names.append([x[4],x[6]])
                else:
                    continue
        #(interface,device,subnet[0],mask[0],nameif,zone)
        for argument in add_interface_arguments:
            for zone_and_name in interface_zone_and_names:
                #Check if it finds the same interface name
                if argument[0] == zone_and_name[1]:
                    #Assigns the zone to the zone field in argument
                    argument[5]=zone_and_name[0]
                    
        for argument in add_interface_arguments:
            add_interface(argument[0],argument[1],argument[2],argument[3],argument[4],argument[5])
            
    if device_type=='F5':
        inside_int=False
        enabled_int=True
        for line in fh:
            if line.startswith('net self'):
                interface=re.findall('/Common/(\S+)',line)
                inside_int=True
            if inside_int==True:
                #Extract all the IPs, including secondary
                if line.startswith('    address'):
                    if routedomain=='default':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)/',line)
                        mask=re.findall('[.][0-9]+/([0-9]+)',line)

                    if routedomain=='1':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%1/',line)
                        mask=re.findall('[.][0-9]+%1/([0-9]+)',line)

                    if routedomain=='2':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%2/',line)
                        mask=re.findall('[.][0-9]+%2/([0-9]+)',line)

                    if routedomain=='3':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%3/',line)
                        mask=re.findall('[.][0-9]+%3/([0-9]+)',line)

                    if routedomain=='4':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%4/',line)
                        mask=re.findall('[.][0-9]+%4/([0-9]+)',line)

                    if routedomain=='5':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%5/',line)
                        mask=re.findall('[.][0-9]+%5/([0-9]+)',line)

                    if routedomain=='6':
                        subnet=re.findall('([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)%6/',line)
                        mask=re.findall('[.][0-9]+%6/([0-9]+)',line)

                if ((inside_int==True) and line.startswith('}')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if len(subnet)>0:
                        #add_interface(interface[0],device,subnet[0],mask[0],interface,'n/a')
                        add_interface(interface[0],device,subnet[0],mask[0],interface[0],'n/a')
                     
                        subnet=[]
                        mask=[]
                        interface=[]
                    else:
                        continue

    if device_type=='Cisco_IOS':
        #Code for ASA follows
        #How an engineer does it, it looks at the configuration, looking for interface commands, then under
        #the command, it looks for ip address  and mask, and also for ip address and mask secondary.
        #After that it just calculates the subnets for each ip,mask
        inside_int=False
        enabled_int=True
        
        for line in fh:
            if line.startswith('interface'):
                line_interface=line.split()
                interface=line_interface[1]
                inside_int=True
                enabled_int=True
                Addlst=list()
                Masklst=list()
            if inside_int==True:
                #Extract all the IPs, including secondary
                #The ip_address_number will count how many IPs, it will create successive
                #interface entries for secondary, terciary interfaces
                ip_address_number=0
                if line.startswith(' ip address'):
                    Address= re.findall('[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+',line)
                    IP=Address[0]
                    Masklen=octectmask2bitlenmask(Address[1])
                    Addlst.append(IP)
                    Masklst.append(Masklen)
                if line.startswith(' shutdown'):
                    #Detects if interface is shutdown
                    enabled_int=False
                if ((inside_int==True) and line.startswith('!')==True):
                    #If reaches end of line ,resets inside_int flag
                    inside_int=False
                    if enabled_int==True:
                        #If interface is not shutdown
                        x=len(Addlst)
                        #This is a list to allow for secondary IP in IOS, i.e 1.2.2.3 255.255.255.0  3.4.5.6
                        i=0
                        if x>0:
                            while i<x:
                                if i==0:
                                    inte=interface
                                if i==1:
                                    inte=interface+' secondary'
                                if i>1:
                                    inte=interface+' secondary '+chr(i)
                                add_interface(inte,device,Addlst[i],Masklst[i],interface,'n/a')
                                i=i+1
                        Addlst=[]
                        Masklst=[]

#def extract_l4_rule(device,config,device_type,routedomain):

###########################################################################
#Query all rows in the Rules table                                        #
###########################################################################
def select_rules(conn):
   
	cur = conn.cursor()
	cur.execute("SELECT * FROM Rules order by name, source_zone, rule_id")

	rows = cur.fetchall()

	for row in rows:
		print(row)
		
		
###########################################################################
#extract rules from the config file and store them in sqlite              #
###########################################################################

###########################################################################
#Query all rows in the Rules table                                        #
###########################################################################
def select_rules(conn):
   
    cur = conn.cursor()
    cur.execute("SELECT * FROM Rules order by name, source_zone, rule_id")

    rows = cur.fetchall()

    for row in rows:
        print(row)
        
        
###########################################################################
#extract rules from the config file and store them in sqlite              #
###########################################################################

def get_l4_rules(device,config_file,device_type,routemain): 

    #arrays
    configfile_array = []
    access_group_array = []
    access_list_array = []
    ACL_name_array = []
    
    get_first_nine_elements_array = []
    new_array = []

    #vars and lists
    line_no = 0
    rule_id = 0
    access_group_search_string = 'access-group'
    access_list_search_string = 'access-list'
    elements_in_each_line = ''
    no_of_elements = 0
    remaining_sql_values_elements = ''
    listOfProtocols = ['tcp','icmp','udp','ip']
    listOfProtocolsany4 = ['tcpany4','icmpany4','udpany4','ipany4']
    listOfProtocolsplushost = ['tcphost','icmphost','udphost','iphost']
    listOfSources = ['object','object-group']
    listOfDestinationip = ['object','object-group','host']
    listafterDestinationip = ['eq','range','object-group']
    listofDestinationPort = ['permitobject-group']
    
    set_application_search_string = 'set applications application-set'
    

    permit = 'permit'
    deny = 'deny'
    permit_deny_position = 0

    #sql vars
    destination_zone = ''
    sql_values = ''
    sql_values2 = ''
    all_sql_values = ''


    #begin
    
    # create a database connection
    database = "configdb.sqlite"
    conn = None
    try:

        conn = sqlite3.connect(database)
    
    except Exception as DbConnectError:
        logging.exception(DbConnectError)
        raise DbConnectError("DbConnect Failed see - Rules.log")
        return 0    

    #open the config file
    with open(config_file) as f:
        #loop through the config file and add each line to an array
        for line in f:
            configfile_array.append(line)
    
    
    #ASA config file processing
    if device_type.upper() == 'ASA':
    
        # loop through the config file array
        for line in configfile_array:
            # For each line, check if line contains the string 'access_group'
            if access_group_search_string in line:
                # If yes then create a new array of these lines as this forms the start of the ASA sql insert statement values
                access_group_array.append(line)
            else:
                # While we are looping through the config file might aswell create the access_list array too
                # This contains all the access-list lines for all ACLs
                if access_list_search_string in line:
                    access_list_array.append(line)          
    
    
        # This for loop is the main outer loop  
        for access_group_line in access_group_array:
            # create a list of the elements in the current line of this controlling array
            elements_in_each_line = access_group_line.split()
            # begin to create the insert statement and the initial values - device_id, name, source_zone and destination_zone
            sql_values =  (device, elements_in_each_line[1],elements_in_each_line[4] ,destination_zone)
            
            #this line was used for testing so the values would print nicely
            #sql_values =  device + ",'" + elements_in_each_line[1] + "'" + ",'" + elements_in_each_line[4] + "'" + ",'" + destination_zone  + "'"
            #print(sql_values)
    
            # so now go back to the access_list_array and get only the lines for the 
          # current ACL name e.g. ACL_EXAMPLE2 and put them into an array
            ACL_name_array = []
            for access_list_line in access_list_array:
                if elements_in_each_line[1] in access_list_line:
                        ACL_name_array.append(access_list_line)         
                    
            # now loop through the lines for the current ACL name
            for ACL_name_line in ACL_name_array:
                #print(ACL_name_line)
                #so set all the sql values vars to '' so if anything comes out as '' that should not be '' it will stand out in testing
                #and also clears out the previous rows data - apart from rule_id as it is incremental
                protocol = ''
                source_ip = ''
                source_port = ''
                destination_ip = ''
                destination_port = ''
                action = ''
                
                # Set rule_id
                rule_id = rule_id + 1
                # separate the rest of the values on the line into elements
                # this will cause an issue with the subnet and mask because there is a space between them so watch out for that
                remaining_sql_values_elements = ACL_name_line.split()
                no_of_elements = len(remaining_sql_values_elements)
                
                
                #Rules
                    
                # it is not 100% sure where every element is in the list e.g. is extended always in every ASA firewall rule?
                # so find the position of permit/deny as it always appears to be there 
                # e.g. position 2 or 3 - this will try to be an anchor for the remaining values and like a sort of double check                     
                # it also means if permit or deny is not in the rule then set action to null
                if re.search(r"permit", ACL_name_line) != None:
                    permit_deny_position = remaining_sql_values_elements.index(permit)
                    action = remaining_sql_values_elements[permit_deny_position]
                elif re.search(r"deny", ACL_name_line) != None:
                    permit_deny_position = remaining_sql_values_elements.index(deny)
                    action = remaining_sql_values_elements[permit_deny_position]
                else:
                    action = ''
                    
                #print(action)  
                
                # Verify the protocol rules
                # most source_ip rules can be verified here too 
                protocol_position = permit_deny_position + 1                                        
    
                # if listOfProtocols = ['tcp','icmp','udp','ip']
                if remaining_sql_values_elements[protocol_position] in listOfProtocols:
                    protocol = remaining_sql_values_elements[protocol_position]
                    # so while here if the element directly after the protocol is an subnet and mask 
                    # then set the source_ip too - think this is just for juniper but the include here too
                    source_ip_position = protocol_position + 1
                    if re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", remaining_sql_values_elements[source_ip_position]) != None:
                        source_ip = remaining_sql_values_elements[source_ip_position]
                    # also while here if in listOfSources = ['object','object-group']               
                    if remaining_sql_values_elements[source_ip_position] in listOfSources:
                        source_ip_position = protocol_position + 2
                        source_ip = remaining_sql_values_elements[source_ip_position]
                    # if ['tcp','icmp','udp','ip'] & any(*new rule*) & any4
                    if remaining_sql_values_elements[source_ip_position] in ['any','any4']:
                        source_ip = remaining_sql_values_elements[source_ip_position]
                else:                   
                    # if listOfProtocols != ['tcp','icmp','udp','ip'] 
                    protocol = ''
                    # Can also verify the source_ip in this case too
                    if remaining_sql_values_elements[protocol_position] == 'any4':
                        source_ip = 'any4'
    
                #print(protocol)
                
                # Verify the remaining source_ip rules of an ip address then the source address is an IP address
                # check this new rule is correct
                print(source_ip_position)
                if remaining_sql_values_elements[protocol_position] + remaining_sql_values_elements[source_ip_position] in listOfProtocolsplushost:
                    after_source_position = source_ip_position + 1
                    if re.search(r"\b\d{1,3}.\d{1,3}.\d{1,3}\b", remaining_sql_values_elements[after_source_position]) != None:
                        source_ip = remaining_sql_values_elements[after_source_position]
                        subnet_ip_position = after_source_position + 1
                        mask_ip_position = after_source_position + 2
                        subnet_mask = remaining_sql_values_elements[subnet_ip_position] + ' ' + remaining_sql_values_elements[mask_ip_position]
                        if re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", subnet_mask) != None:
                            destination_ip = subnet_mask
                            destination_ip_position = mask_ip_position
                            
                #print(source_ip)
                
                if destination_ip == '':
                    #Verify the destination_ip  
                    #       listOfDestinationip = ['object','object-group','host']
                    destination_ip_position = source_ip_position + 1
                    if remaining_sql_values_elements[destination_ip_position] not in listOfDestinationip:
                        destination_ip = remaining_sql_values_elements[destination_ip_position]
                    else:
                        destination_ip_position = source_ip_position + 2    
                        destination_ip = remaining_sql_values_elements[destination_ip_position]
    
                #print(destination_ip)
            
                #Verify the destination_port
                #if protocol == 'ip' - don't think need to test for this rule because it is set to '' at the start
                # If there are not enough elements this part of the code would fail so do a check first
                # otherwise destination_port = '' already set at the start
                #print(no_of_elements)
                # no convinved about this being 9 is correct but the values are all there apart from 2 & 3 ACL_EXAMPLE2
                if no_of_elements > 9:
                    after_destination_ip_position = destination_ip_position + 1
                    # listafterDestinationip = ['eq','range','object-group']
                    if remaining_sql_values_elements[after_destination_ip_position] in listafterDestinationip:  
                        destination_port_position = destination_ip_position + 2
                        destination_port = remaining_sql_values_elements[destination_port_position]
                    #   listofDestinationPort = ['permitobject-group']
                    if remaining_sql_values_elements[permit_deny_position] + remaining_sql_values_elements[protocol_position] in listofDestinationPort:
                        after_permitobjectgroup_position = permit_deny_position + 2
                        destination_port = remaining_sql_values_elements[after_permitobjectgroup_position]
        
                #print(destination_port)
                
                #sql_values2 = sql_values + "," + str(rule_id) + ",'" + protocol + "'" + ",'" + source_ip + "'" + ",'" + destination_ip + "'" + ",'" + source_port + "'" + ",'" + destination_port + "'" + ",'" + action + "'"
                
                sql_values2 =  ( str(rule_id),protocol, source_ip, destination_ip, source_port , destination_port, action)
                all_sql_values = sql_values + sql_values2
                #
                print(sql_values2)
                
                # use the connection
                with conn:

                    print("Insert to Rules")
                
                    try:
                        sql = ''' INSERT INTO Rules(device_id,name,source_zone,destination_zone,rule_id,protocol,source_IP,destination_IP,source_port,destination_port,action) VALUES (?,?,?,?,?,?,?,?,?,?,?) '''
                        cur = conn.cursor()
                        cur.execute(sql, all_sql_values)
                        conn.commit()
                        
                    except sqlite3.OperationalError as DbInsertError:
                        logging.exception(DbInsertError)
                        raise DbInsertError("DbInsert Failed see - Rules.log")
                        return 0
                            
                    sql_values2 = '' 
                 
        rule_id = 0
        conn.close()
        
        
    else:

        # Juniper config file
        data = []
        line_no = 0
        for line in configfile_array:       
            line_no = line_no + 1
            # get the first 9 elements from each line in the array
            if line_no != 1:
                elements_in_each_line = line.split()
                new_array = elements_in_each_line[:9]
                get_first_nine_elements_array.append(new_array)

        #numpy
        for line2 in get_first_nine_elements_array:
            data.append(line2)
            
        #The majority of the rows have the same data use numpy to quickly remove duplicates for the first 9 columns
        data = np.array(data)
        new_array = [tuple(row) for row in data]

        #remove all the duplicate rows
        unique_rows = np.unique(new_array, axis=0)
            
        #The 2 rows come out the wrong way about so sort them so this can become the outer loop array
        sortedArr = unique_rows[unique_rows[:,8].argsort()]
            
        #set applications application-set WEB-PORTS application TCP-443     
        for line in configfile_array:
            elements_in_each_line = line.split()
            if set_application_search_string in line:
                set_application = elements_in_each_line[3]
                # Substring to return TCP
                application = elements_in_each_line[5][0:3]
                destination_port = elements_in_each_line[5][4:]

        for outer_loop in sortedArr:
            policy_name = outer_loop[8]

            sql_values =  (device,policy_name[8], outer_loop[4],outer_loop[6])
            
            # Set rule_id
            rule_id = rule_id + 1
            
            # Step throughfinding the rest of the values to insert to the rules table for each line.    
            for line in configfile_array:
                elements_in_each_line = line.split()
                if policy_name in line:
                    match_source_address = 'source-address'
                    if match_source_address in line:
                        source_ip = elements_in_each_line[11]
                    match_destination_address = 'destination-address'
                    if match_destination_address in line:
                        destination_ip = elements_in_each_line[11]
                    match_permit = 'then'
                    if match_permit in line:
                        action = elements_in_each_line[10]
                    match_application = 'match application'                      
                    if match_application in line:
                        application_name = elements_in_each_line[11]
                        if application_name == set_application:
                            protocol = application
                        else:
                            protocol = elements_in_each_line[11][0:3]
                            destination_port = elements_in_each_line[11][4:]
                
            #print(protocol)
            #print(source_ip)
            #print(destination_ip)
            #print(destination_port)
            #print(action)
            source_port = ''
                
            #STR(RULE_ID) This can come off now, it was just used for printing because I couldn't join a number iwth a string
            sql_values2 = (str(rule_id), protocol,source_ip , destination_ip ,source_port ,destination_port , action )
                
            all_sql_values = sql_values + sql_values2
                
            # use the connection
            with conn:

                print("1. Insert to Rules")
                
                try:
                    sql = ''' INSERT INTO Rules(device_id,name,source_zone,destination_zone,rule_id,protocol,source_IP,destination_IP,source_port,destination_port,action) VALUES (?,?,?,?,?,?,?,?,?,?,?) '''
                    cur = conn.cursor()
                    cur.execute(sql, all_sql_values)
                    conn.commit()
                except sqlite3.OperationalError as DbInsertError:
                    logging.exception(DbInsertError)
                    raise DbInsertError("DbInsert Failed see - Rules.log")
                    return 0    
        
            sql_values2 = '' 

                
        rule_id = 0
                
        
        
        print("2. Query rules")
        select_rules(conn)
        conn.close()



############Functions to manipulate the database###############

def add_interface(name,device,ip_address,ip_mask,nameif,zone):
    #Receives and string like: (GigabitEthernet0/7 572118  10.159.0.1  25 nameif )
    mask=bitlenmask2obtectmask(ip_mask)
    subnet=host2subnet(ip_address,mask)
    subnet_id=get_subnet_id(subnet[0])
    device_id=get_device_id(device)
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert route in Routes
    cur.execute('INSERT INTO Interfaces (name,device_id,subnet_id,ip_address,ip_mask,nameif,zone) VALUES (?,?,?,?,?,?,?)',(name,device_id,subnet_id,ip_address,ip_mask,nameif,zone))
    conn.commit()
def add_device(hostname,configfile,maker):
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #add device in Devices
    cur.execute('INSERT INTO Devices (hostname,configfile,maker) VALUES ( ?,?,? )', (hostname,configfile,maker))
    print((hostname,configfile,maker))
    conn.commit()

def add_subnet(name,subnet,mask):
    #Returns the subnet_id of a subnet in the table Subnets
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert subnet in Subnets
    cur.execute('INSERT OR IGNORE INTO Subnets (name,subnet,mask) VALUES (?,?,?)' , (name,subnet,mask))
    conn.commit()

def add_route(subnet,mask,nexthop,administrative_distance,device_hostname):
    #It always makes sure that the subnet exist by calling add_subnet() first
    device_id=get_device_id(device_hostname)
    add_subnet(subnet,subnet,mask)
    subnet_id=get_subnet_id(subnet)
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert route in Routes
    cur.execute('INSERT INTO Routes (subnet_id,nexthop,administrative_distance,device_id) VALUES (?,?,?,?)',(subnet_id,nexthop,administrative_distance,device_id))
    conn.commit()

def get_subnet_id(net):
    #Returns the subnet_id of a subnet in the table Subnets
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert subnet in Subnets
    cur.execute('SELECT id FROM Subnets WHERE subnet = ?',(net,))
    subnet_id=cur.fetchone()
    conn.commit()
    return subnet_id[0]

def get_device_id(device):
    #Returns the device_id of a subnet in the table Subnets
    conn = sqlite3.connect('configdb.sqlite')
    cur = conn.cursor()
    #insert subnet in Subnets
    cur.execute('SELECT id FROM Devices WHERE hostname = ?',(device,))
    device_id=cur.fetchone()
    conn.commit()
    return int(device_id[0])
    
#Main program starts, this program will populate the database tables that will be used by the querier module
#to find what devices are in the path between modules

########Definition of devices###############

Device_list=[('572120','572120_network.txt','ASA','default'),('572118','572118_network.txt','ASA','default'),
             ('825183','825183_network.txt','JUNIPER','default'),('725763','725763_network.txt','ASA','default'),
             ('1105400','1105400_network.txt','ASA','default'),('572126default','572126_network.txt','F5','default'),
             ('572126%1','572126_network.txt','F5','1'),('572126%2','572126_network.txt','F5','2'),
             ('572126%3','572126_network.txt','F5','3'),('572126%4','572126_network.txt','F5','4'),
             ('572126%5','572126_network.txt','F5','5'),('572126%6','572126_network.txt','F5','6'),
             ('RS_LON5_705883_CS','RS_LON5_705883_CS.txt','Cisco_IOS','default'),
             ('GBLon03-CSW01','GBLon03-CSW01.txt','Cisco_IOS','default'),
             ('698258','698258_network.txt','ASA','default'),('698259','698259_network.txt','ASA','default'),
             ('825186','825186_network.txt','JUNIPER','default'),
             ('ips01-dc3-asa-1-pri','ips01-dc3-asa-1-pri.txt','ASA','default'),
             ('698261default','698261_network.txt','F5','default'),('698261%1','698261_network.txt','F5','1'),
             ('698261%2','698261_network.txt','F5','2'),('698261%3','698261_network.txt','F5','3'),
             ('698261%4','698261_network.txt','F5','4'),('698261%6','698261_network.txt','F5','6')]
#Device_list=[('572120san','572120san_network.txt','ASA','default'),('825183san','825183san_network.txt','JUNIPER','default')]
#             ('825183','825183_network.txt','JUNIPER','default')
#V8 is adding source and destination protocols
#Another module would extract the routes, firewalls and next hops and store
#in a database
#
#################Create database ################


conn = sqlite3.connect('configdb.sqlite')
cur = conn.cursor()

# Make some fresh tables using executescript()
# Create Tables for Devices, Interfaces, Routes,Subnets
cur.executescript('''
DROP TABLE IF EXISTS Devices;
DROP TABLE IF EXISTS Interfaces;
DROP TABLE IF EXISTS Subnets;
DROP TABLE IF EXISTS Routes;
DROP TABLE IF EXISTS Rules;
DROP TABLE IF EXISTS Network_Objects;
DROP TABLE IF EXISTS Service_Objects;

CREATE TABLE Devices (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    hostname  TEXT UNIQUE,
    configfile TEXT,
    maker   TEXT
);

CREATE TABLE Interfaces (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name   TEXT ,
    device_id INTEGER,
    subnet_id INTEGER,
    ip_address TEXT,
    ip_mask TEXT,
    nameif TEXT,
    zone TEXT
);

CREATE TABLE Subnets (
    id  INTEGER NOT NULL PRIMARY KEY
        AUTOINCREMENT UNIQUE,
    name TEXT  ,
    subnet  INTEGER,
    mask  INTEGER,
    UNIQUE (subnet,mask)  
);
CREATE TABLE Routes (
    id  INTEGER NOT NULL PRIMARY KEY
        AUTOINCREMENT UNIQUE,
    subnet_id TEXT,
    nexthop TEXT,
    administrative_distance INTEGER,
    device_id INTEGER
);
CREATE TABLE Rules (
    id  INTEGER NOT NULL PRIMARY KEY  AUTOINCREMENT UNIQUE,
    device_id TEXT,
    name TEXT,
    source_zone TEXT,
    destination_zone TEXT,
    rule_id INTEGER,
    protocol TEXT,
    source_IP TEXT,
    destination_IP TEXT,
    source_port TEXT,
    destination_port TEXT,
    action TEXT
);
CREATE TABLE Network_Objects (
    id  INTEGER NOT NULL PRIMARY KEY  AUTOINCREMENT UNIQUE,
    device_id TEXT,
    name TEXT,
    object_type TEXT,
    ip_version TEXT,
    ip TEXT,
    mask TEXT   
);
CREATE TABLE Service_Objects (
    id  INTEGER NOT NULL PRIMARY KEY  AUTOINCREMENT UNIQUE,
    device_id TEXT,
    protocol TEXT,
    ports TEXT 
    );
''')

#########Extraction of information in table########
#########Extraction of information in table########

for deviceinfo in Device_list:
    #This is how the tuples in device list look like ('572120','572120.txt','ASA','default')
    add_device(deviceinfo[0],deviceinfo[1],deviceinfo[2])

conn.commit()


#Device info looks like: ('572120','572120_network.txt','ASA','default')
#for deviceinfo in Device_list:
#    extract_route_static(deviceinfo[0],deviceinfo[1],deviceinfo[2],deviceinfo[3])
#for deviceinfo in Device_list:
 #   extract_route_connected(deviceinfo[0],deviceinfo[1],deviceinfo[2],deviceinfo[3])
#for deviceinfo in Device_list:
 #   extract_interface(deviceinfo[0],deviceinfo[1],deviceinfo[2],deviceinfo[3])
for deviceinfo in Device_list:
    if deviceinfo[2]=='ASA':
        config_file = deviceinfo[1]
        resp = 2
        device_type = 'ASA'
        device = get_device_id(deviceinfo[0])    
        
        try:
        
            resp = get_l4_rules(device,config_file,device_type,deviceinfo[3]) 
            if resp == 0:
                raise GetRulesASAError("Get_Rules Failed for ASA see - Rules.log")
        except Exception as GetRulesASAError:
            logging.exception(GetRulesASAError)

#get the rules from the Juniper config file 
    if deviceinfo[2]=='JUNIPER':
        config_file = deviceinfo[1]    
        resp = 2
        config_file = deviceinfo[1]
        device_type = 'JUNIPER'    
        device =  get_device_id(deviceinfo[0])    
        
        try:

            resp = get_rules(device,config_file,device_type,routemain) 
            if resp == 0:
                raise GetRulesJunError("Get_Rules Failed for Juniper see - Rules.log")
        except Exception as GetRulesJunError:
            logging.exception(GetRulesJunError)
conn.commit()



#Test function


#Need to standarize the output of all the functions-Done
#Need to create the function for the Cisco Switch as well-Done
#I tested the loop and no errors in the extract_route_static funtion, need to add the database commands to-Done, there is a dependency in
#having subnets ID , in order to progress, need to add subnets to the subnets table as i create routes.-Done
#Populate the table with routes, with a test subnet_id. -Done
#Create scripts to extract connected subnets from devices and add to tables-Done
    #Done for Cisco Switch
    #Pending F5
    #Pending Juniper
    #Pending ASA
# There was an issue with duplicated subnets, due duplicated F5 interfaces. fixed with insert 
# Ignore and with making in subnet, the subnet and mask unique.-Done
# There was an addition of a administrative_distance in the route table, to deal with the routes added when
# extracting subnets vs extracting interfaces-Done
#Found error in mask of an output , done on 1st February, version 3-Done
#Create funtions to add_interface -Done
#using the subnet, and not the mask, issues will happen when subnet1 = subnet2, but they have different mask
#For instance 10.2.3.0 255.255.255.0 and 10.2.3.0 255.255.255.128 -Done
#Next task: Create funcion to extract_interfaces()-Done
##Issues with extraction. 1. Juniper and F5 not showing in the interface table -Fixed   2. in Route table the device
#id, is not the table id from the device table.

#Flow:(source ip,gateway,protocol,source port,destination_ip,destination_port)
#Function to tell if two host are in same subnet , if_in_net -Done

#Check if source_ip and gateway are in same subnet.
#For a source_ip make a loop in all the subnets and will find the subnet.

#Once it finds the subnet, will find what interfaces belong to this subnet, then will give the device names

#If there are more than two devices , it will answer for the default gateway of the source host, if not, will assume that
#Traffic goes via the only device in the subnet

#Will then lookup in the routing table of the Device to find next hop

#Create function to relate subnet with ip and ip with interface.
#Create function to lookup routes
#The create program to calculate the path, perhaps i should just populate a permanent table with the paths.

#Version control.
#v4 created the function add_interface

#Know issues
#An issue to fix is that the subnet and mask are unique, at the moment the get_subnet_id function is only
#using the subnet
#Issue with the spaces in columns with IP addresses, causing failures of function who_has

#Improvement list
#-Add in juniper the description to nameif
#Add in ASA to the zone, the access-list name applied to the interface
#Add in IOS to the zone, the access-list name applied to the interface
#What will happen if the subnets are duplicated in different devices. It should then have the possiblity of have it
#Added, so the unique condition has to also be subnet, mask and device, then it will allow for duplicate subnets.
#Changed type to device_type as type can be reserver word.