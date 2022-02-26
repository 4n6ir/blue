#!/usr/bin/bash
if [ -f /var/run/reboot-required ]
then
        init 6
fi