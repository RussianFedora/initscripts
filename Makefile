# Makefile for source rpm: initscripts
# $Id$
NAME := initscripts
SPECFILE = $(firstword $(wildcard *.spec))

include ../common/Makefile.common
