from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_tags:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag not in self.void_tags:
            if self.stack and self.stack[-1][0] == tag:
                self.stack.pop()
            else:
                print(f"Unmatched end tag: </{tag}> at line {self.getpos()}. Current stack top: {self.stack[-1] if self.stack else 'empty'}")

def check_file(filepath):
    print(f"Checking {filepath}")
    parser = MyHTMLParser()
    with open(filepath, 'r', encoding='utf-8') as f:
        parser.feed(f.read())
    print(f"Remaining unclosed tags in {filepath}: {parser.stack}")
    print("-" * 40)

if __name__ == '__main__':
    check_file('agrochain-pulse/app/static/agent_dashboard.html')
    check_file('agrochain-pulse/app/static/supervisor_dashboard.html')
