import fitz

doc = fitz.open('test_table_d4.pdf')
print('=== INSPECTING test_table_d4.pdf ===')
print('Page count:', len(doc))

page = doc[0]
blocks = page.get_text('blocks')
for b in blocks:
    text = b[4].strip().replace('\n', ' ')
    print(f'Block ({b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}) -> {repr(text[:70])}')
