package org.apache.cassandra.stress.operations.predefined;
/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */


import java.io.File;
import java.io.FileNotFoundException;
import java.io.PrintWriter;
import java.nio.ByteBuffer;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.List;

import org.apache.cassandra.stress.generate.PartitionGenerator;
import org.apache.cassandra.stress.generate.SeedManager;
import org.apache.cassandra.stress.settings.Command;
import org.apache.cassandra.stress.settings.StressSettings;
import org.apache.cassandra.stress.util.Timer;
import org.apache.cassandra.utils.Tracer;

//import org.apache.logging.log4j.LogManager;
//import org.apache.logging.log4j.Logger;

public class CqlReader extends CqlOperation<ByteBuffer[][]>
{
    //static Logger logger = LogManager.getLogger(CqlReader.class);
    static List<ByteBuffer> keys = new ArrayList();

    public CqlReader(Timer timer, PartitionGenerator generator, SeedManager seedManager, StressSettings settings)
    {
        super(Command.READ, timer, generator, seedManager, settings);
    }

    @Override
    protected String buildQuery()
    {
        StringBuilder query = new StringBuilder("SELECT ");

        if (settings.columns.slice)
        {
            query.append("*");
        }
        else
        {
            for (int i = 0; i < settings.columns.maxColumnsPerKey ; i++)
            {
                if (i > 0)
                    query.append(",");
                query.append(wrapInQuotes(settings.columns.namestrs.get(i)));
            }
        }

        query.append(" FROM ").append(wrapInQuotes(type.table));
        query.append(" WHERE KEY=?");
        return query.toString();
    }

    @Override
    protected List<Object> getQueryParameters(byte[] key)
    {
        return Collections.<Object>singletonList(ByteBuffer.wrap(key));
    }

    @Override
    protected CqlRunOp<ByteBuffer[][]> buildRunOp(ClientWrapper client, String query, Object queryId, List<Object> params, ByteBuffer key)
    {
        synchronized (keys) {
            keys.add(key);
            //logger.info("key=[{}] {}", Tracer.toHex(key), key);
        }

        List<ByteBuffer> expectRow = getColumnValues();
        //for (ByteBuffer bb: expectRow) {
        //    logger.info("[{}] {}"
        //            , Tracer.toHex(bb), bb);
        //}

        return new CqlRunOpMatchResults(client, query, queryId, params, key, Arrays.asList(expectRow));
    }

    public static void PrintKeys() throws FileNotFoundException {
        if (keys.size() == 0)
            return;

        DateFormat dateFormat = new SimpleDateFormat("yy-MM-dd-HH:mm:ss");
        Date date = new Date();
        String fnOut = String.format("read-keys-%s", dateFormat.format(date));
        try (PrintWriter pw = new PrintWriter(fnOut)) {
            for (ByteBuffer k: keys)
                pw.println(Tracer.toHex(k));
        }
        System.out.printf("Created file %s %d\n", fnOut, (new File(fnOut)).length());
    }
}
