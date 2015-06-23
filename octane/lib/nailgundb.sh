#!/bin/bash

PG_CMD="psql -At postgresql://nailgun:$(get_nailgun_db_pass)@localhost/nailgun"
