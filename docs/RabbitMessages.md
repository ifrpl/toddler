# Crawl

## CrawlRequest

    {
        "url": "http(s)://example.org/home.html",
        "cookies": {
            "sessid": "1mnidnf98023fdsafdf"
        }
        "referer": "http://example.org/index.html",
        "method": "GET",
        "actions": ["follow", "index"],
        "timeout": "2015-03-24T11:43:27.746219+00:00" 
    }
    {
        "url": "http(s)://example.org/home.html",
        "cookies": {
            "sessid": "1mnidnf98023fdsafdf"
        }
        "referer": "http://example.org/index.html",
        "method": "POST",
        "data": {
            "date": "2014-02-02"
        },
        "actions": ["follow", "index"],
        "timeout": "2015-03-24T11:43:27.746219+00:00"
    }
    {
        "url": "http(s)://example.org/home.html",
        "cookies": {
            "sessid": "1mnidnf98023fdsafdf"
        }
        "referer": "http://example.org/index.html",
        "method": "POST",
        "json": "{\"date\":\"2014-02-02\"}",
        "timeout": "2015-03-24T11:43:27.746219+00:00" 
    }
    
## CrawlResult

    {
        "url": "http(s)://example.org/home.html",
        "cookies": {
            "sessid": "123dsafsdf",
            "csrftoken": "dfsdf9023"
        },
        "status_code": 200,
        "html": "<html>...</html>",
        "actions": ["follow", "index"],
        "headers": {'content-type': "text/html"}
        "crawl_time": "2015-03-24T11:43:27.746219+00:00"
    }
    
Note, that headers are a direct copy from server, and as they are from `requests.Session` they should be in lowercase, but still this is a external library and this behaviour might change.

# Analysis
    
## AnalysisRequest
 
    {
        "url": "http(s)://example.org/home.html",
        "html" "<html>...</html>",
        "headers": {"content-type": "text/html"},
        "crawl_time": "2015-03-24T11:43:27.746219+00:00"
    }
   
# Index

## IndexTask

    {
        "url": "http(s)://example.org/home.html",
        "action": "delete|upsert",
        "document": {}
    }
    
# Mongo Objects

## Host
    {
        "_id": 123123123,
        "host": "example.com",
        "block": False,
        "block_date": "2015-03-24T11:43:27.746219+00:00",
        "number_of_documents": 3434,
        "number_of_indexed_documents": 2322,
        "request_delay": 0,
        "agressive_crawl": False,
        "config": {"crawlConfig": [
          {
              "patterns": [
                  "http:\/\/example.com\/.*\.html"
              ],
              "actions": ["follow", "index"]
          },
          {
              "patterns": [
                  "http:\/\/example.com\/nocrawl\/.*\.html"
              ],
              "actions": ["nofollow"]
          }
        ]},
        "ignoreRobots": False,
        "robots_txt": {
            "status": "waiting|downloaded"
            "status_code": 200,
            "content": "User-Agent: *\nAllow: /\n",
            "expires": "2015-04-24T11:43:27.746219+00:00"
        },
        "last_crawl_job_date": "2015-03-24T11:43:27.746219+00:00"
    }
