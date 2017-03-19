
SOURCE = $(wildcard *.ui)
TARGET = $(subst ui,py,$(SOURCE))

all : $(TARGET)
clean :
	rm -f $(TARGET)
re: clean all

#.SUFFIXES: .py .ui

%.py : %.ui
	pyuic4 $< -o $*.py
