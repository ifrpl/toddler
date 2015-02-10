# Architecture Overview

We can divide the system to three parts:

  1. Crawling
    - Crawl
    - Analyse
  1. Indexing
  1. Search

First two parts are connected with each other using 
[Rabbit](https://www.rabbitmq.com) queue manager.
Search is using [ElasticSearch](http://www.elasticsearch.org) that is feeding
on database filled by Indexer.

Whole system is fail free due to it's granularity. There are no big processess
That are single, every process can be multiplied as much as we want because
of round-robin nature of _RabbitMQ_.

## Crawling

Crawling starts with __CrawlManager__ this process written in python is
connected to _RabbitMQ_.

### CrawlManager

Job of this process is:

  - Receive _CrawlRequests_
  - Schedule _CrawlTasks_
  - Process _CrawlResult_
  - Schedule _AnalysisTask_
  - Process _AnalysisResult_
  - Schedule _IndexTask_
  
CrawlTasks are pushed to _RabbitMQ_ so crawlers can pick them up.

### Crawler

We can support multiple crawlers that are written in different languages. 
For start we will have one written in python, but for JS support there should
 be one written in Node.js+CasperJS.

Thanks to _RabbitMQ_ architecture we can run as many crawler on many machines
as we want.

### Analyser

Also here we can support multiple analysers. Currently we've got one in python.
It picks up _AnalysisTask_ from _RabbitMQ_ and returns _AnalysisResult_ which
consists out of _Document_ and _meta_ information about analysis.
In _meta_ analyser add information about quality of the document and flag that
says if it should be processed or not.

_AnalysisResult_ is processed by __CrawlManager__ and then if document meets
indexing criteria (so for now the flag ti be index), _IndexTask_ is pushed
to _RabbitMQ_

## Indexing

Indexing is done by __IndexManager__ when it will receive  _IndexTask_.

### IndexManager

All it does is pushing documents to _MongoDB_ so then _ElasticSearch_ can pick
them up.

# Connections between processes chart

![Communication chart][connection]

[connection]: ./communication.chart.png "Communication"

# Crawl Sequence chart - No follow

![Sequence chart](./crawl-no-follow-sequence.chart.png)