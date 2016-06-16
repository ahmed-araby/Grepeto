__author__ = 'ahmed'
import pymongo
import urlparse
from slugify import slugify
from grep.settings import DB


class MongoPipeline(object):
    collection = None

    def __init__(self):
        client = pymongo.MongoClient()
        db = client[DB['connection']['db']]
        self.collection = db[DB['collection']['articles']]
        self.auto_increment = db[DB['collection']['increment']]
        self.categories = db[DB['collection']['categories']]
        self.websites = db[DB['collection']['websites']]
        pass

    def get_new_increment(self, collection):
        return int(self.auto_increment.find_and_modify(
            query={'_id': collection},
            update={'$inc': {'current_id': 1}},
            fields={'current_id': 1},
            new=True,
            upsert=True
        ).get('current_id'))

    def getCategory(self, catName, domain):
        cat = self.categories.find_one({'original.name': catName, 'domain': domain},
                                       {'original':
                                           {
                                               '$elemMatch': {'name': catName}
                                           }
                                       })
        if not cat:
            raise Exception('can not find articles category ['+catName+']')
        # print cat
        # if not cat:
        #     cat = {
        #         '_id': self.get_new_increment(DB['collection']['categories']),
        #         'parentId': 0,
        #         'active': 1,
        #         'name': catName,
        #         'slug': slugify(catName)
        #     }
        #     self.categories.insert(cat)
        return cat

    def getArticleId(self, url):
        old_item = self.collection.find_one({'url': url})
        if old_item is None:
            return self.get_new_increment(DB['collection']['articles'])
        else:
            return old_item.get('_id')

    def getWebsite(self, item):
        url_parts = urlparse.urlparse(item['url'])
        domain = url_parts[1]
        website = self.websites.find_one({'domain': domain})
        if not website:
            website_link = url_parts[0] + '://' + url_parts[1]
            website = {
                '_id': self.get_new_increment(DB['collection']['websites']),
                'domain': domain,
                'url': website_link,
                'icon': '',
                'description': '',
                'name': ''
            }
            self.websites.insert(website)
        return website

    def process_item(self, item, spider):
        item_id = self.getArticleId(item['url'])
        website = self.getWebsite(item)
        cat = self.getCategory(item['category'], website['domain'])
        item['categoryId'] = cat['_id']
        item['originalCategoryId'] = cat['original']['_id']
        item['websiteId'] = website['_id']
        self.collection.update({'_id': item_id},
                               {'$set': dict(item)}, upsert=True)
        return item
