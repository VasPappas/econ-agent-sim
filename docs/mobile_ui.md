# Phone-friendly Streamlit workspace

The app uses native Streamlit controls, tables, charts and downloads, with a
restrained cream and green stylesheet. Main content is a single reading column;
paired metrics stack on narrow screens, while the two advance buttons stay together. There is no custom
JavaScript results component or separate mobile app.

Setup presents six number inputs with plain-language help, followed by visible
starting totals. Presets require an explicit **Use this setup** action. Draft
values survive navigation. Results use a completed-period selector and explicit
period/cumulative range; short account summaries precede expandable detail.
Native tables can scroll horizontally without widening the whole page.

Validation combines AppTest interaction checks with browser review. AppTest
checks behavior, not pixel layout; mobile screenshots and overflow inspection
remain useful release checks. The app is not yet an installable offline application.
