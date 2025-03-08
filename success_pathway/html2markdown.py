import html2text

html_content = """
<div class="markdown prose w-full break-words dark:prose-invert dark"><p data-start="0" data-end="83">In Python, you can print data using the <code data-start="40" data-end="49">print()</code> function. Here's a basic example:</p><pre class="!overflow-visible" data-start="85" data-end="290"><div class="contain-inline-size rounded-md border-[0.5px] border-token-border-medium relative bg-token-sidebar-surface-primary dark:bg-gray-950"><div class="flex items-center text-token-text-secondary px-4 py-2 text-xs font-sans justify-between rounded-t-[5px] h-9 bg-token-sidebar-surface-primary dark:bg-token-main-surface-secondary select-none">python</div><div class="sticky top-9 md:top-[5.75rem]"><div class="absolute bottom-0 right-2 flex h-9 items-center"><div class="flex items-center rounded bg-token-sidebar-surface-primary px-2 font-sans text-xs text-token-text-secondary dark:bg-token-main-surface-secondary"><span class="" data-state="closed"><button class="flex gap-1 items-center select-none px-4 py-1" aria-label="Copy"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="icon-xs"><path fill-rule="evenodd" clip-rule="evenodd" d="M7 5C7 3.34315 8.34315 2 10 2H19C20.6569 2 22 3.34315 22 5V14C22 15.6569 20.6569 17 19 17H17V19C17 20.6569 15.6569 22 14 22H5C3.34315 22 2 20.6569 2 19V10C2 8.34315 3.34315 7 5 7H7V5ZM9 7H14C15.6569 7 17 8.34315 17 10V15H19C19.5523 15 20 14.5523 20 14V5C20 4.44772 19.5523 4 19 4H10C9.44772 4 9 4.44772 9 5V7ZM5 9C4.44772 9 4 9.44772 4 10V19C4 19.5523 4.44772 20 5 20H14C14.5523 20 15 19.5523 15 19V10C15 9.44772 14.5523 9 14 9H5Z" fill="currentColor"></path></svg>Copy</button></span></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="!whitespace-pre language-python"><span><span class="hljs-comment"># Example 1: Printing a string</span>
<span class="hljs-built_in">print</span>(<span class="hljs-string">"Hello, World!"</span>)

<span class="hljs-comment"># Example 2: Printing numbers</span>
<span class="hljs-built_in">print</span>(<span class="hljs-number">123</span>)

<span class="hljs-comment"># Example 3: Printing multiple items</span>
name = <span class="hljs-string">"Alice"</span>
age = <span class="hljs-number">30</span>
<span class="hljs-built_in">print</span>(<span class="hljs-string">"Name:"</span>, name, <span class="hljs-string">"Age:"</span>, age)
</span></code></div></div></pre><p data-start="292" data-end="456" data-is-last-node="">You can print different types of data like strings, numbers, or even the contents of variables. If you need help with a specific use case or data, feel free to ask!</p></div>
"""

# Initialize the HTML2Text object
h = html2text.HTML2Text()

# Settings to ensure proper conversion
h.body_width = 0        # Disable line wrapping
h.ignore_links = False  # Don't ignore links
h.ignore_images = False # Don't ignore images (optional)

# Convert HTML to Markdown
markdown_content = h.handle(html_content)

print(markdown_content)
