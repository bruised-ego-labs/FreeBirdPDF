# Project FreeBird: The PDF Editor They Don't Want You To Have

_A [Bruised Ego Labs](https://github.com/bruised-ego-labs) Production_  
_Version 0.3.0 - Third Flight_

**(Codename: Acrobat's Nightmare: The Re-Factoring)**

![Patch the Eagle - Our legally distinct mascot](resources/FreeBird.png)
_(Patch the Eagle says: "Freedom isn't free, but your PDF editor definitely is. And now with a much cleaner codebase!")_

---

## What Our Users Are Saying\*

> "After using the modular version of FreeBirdPDF, not only did I cancel my Adobe subscription, but my code maintenance anxiety disappeared too!"  
> — _Software Developer in Distress, Probably_

> "I rearranged 400 pages in my dissertation AND signed it digitally with FreeBirdPDF. My advisor still hates it, but now it's perfectly ordered, authenticated garbage."  
> — _PhD Candidate, University of Perpetual Studies_

> "The new e-signature feature saved my marriage AND my job. My spouse said either the $20/month PDF software subscription goes, or they do. My boss said either I start signing documents properly, or I go."  
> — _Someone Who Definitely Exists_

_\*Not actual testimonials. Patch the Eagle may have made these up during his refactoring coffee break._

---

## Attention Adobe® Acrobat® Users: Your Reign of Subscription Tyranny Is Now Under More Organized Siege.

You gaze upon **Project FreeBird 0.3.0**, a technological marvel painstakingly assembled using Python, PyQt6, and the surprisingly potent PyMuPDF library—now with a modular architecture that won't make future contributors break down in tears!

We at Bruised Ego Labs dared to ask: "What if viewing, assembling, rearranging, occasionally deleting, and now SIGNING pages in PDFs didn't require a second mortgage?"

This project is the answer nobody at Adobe wanted to hear. It's proof that sometimes, "good enough" is actually... well, better organized than before.

---

## Features That Will Send Shockwaves Through Silicon Valley\*

(\*Shockwaves may be localized and primarily consist of mild surprise at our new directory structure.)

Prepare to be moderately whelmed by capabilities previously thought only possible within heavily marketed software suites:

- **Multi-Document Viewing:** Open _multiple_ PDFs! At the _same time_! In _tabs_! Groundbreaking.
- **Pixel-Perfect\* Page Viewing:** See your PDFs rendered on screen. (_Pixel perfection dependent on screen, zoom level, and PyMuPDF's mood._)

- **Revolutionary Navigation:** Click "Next." Click "Previous." Type a page number and click "Go." Use the Left/Right arrow keys. Even **Home** and **End** keys work! We've spared no expense*. (*Expense spared: R&D department\*)

- **The Power of Deletion:** Eradicate unwanted pages with the terrifying click of a "Delete Page" button! (Subject to confirmation, we're not monsters).

- **Page Reordering Wizardry:** Move pages up! Move pages down! Drag pages to new positions! Rearrange entire presentations in minutes, not hours! All without paying $239/year!

- **Text Search Technology:** Find words inside your documents! Watch as results highlight in real-time! Navigate with magical "Next" and "Previous" buttons!

- **Radical Saving Technology:** Use "Save" or "Save As..." to preserve your masterful deletions, assemblies, and reorderings under the _same_ or _different_ name. Genius!

- **Document Assembly:** Right-click on a page in one tab, add it (or the whole document!) to a dedicated "Assembly" tab. Build your Franken-PDFs with unprecedented* ease! (*Ease may vary.\*)

- **Zoom Control:** Make things bigger. Make things smaller. Mind. Blown.

- **Keyboard Shortcuts for Power Users:** Ctrl+S to save! Ctrl+Shift+Up/Down to move pages! Ctrl+F to search! F3 to find next! It's almost like we care about efficiency!

- **COMING SOON - E-Signatures:** Sign documents electronically! Add signature images! Include validation metadata! All without selling your firstborn to Adobe!

---

## New and Improved Project Structure

Behold, the architectural marvel that is our new project structure! Gone are the days of a single 2,000-line Python file. Feast your eyes upon this masterpiece of organization:

```
FreeBirdPDF/
│
├── FreeBirdPDF.py            # Main entry point (now mercifully brief)
├── requirements.txt          # Dependencies list (coming soon!)
│
├── freebird/                 # Main package directory
│   ├── __init__.py           # Makes the directory a package
│   ├── constants.py          # Constants and config values
│   │
│   ├── ui/                   # UI components
│   │   ├── __init__.py
│   │   ├── main_window.py    # PDFViewer class
│   │   ├── pdf_view.py       # PDFViewWidget class
│   │   ├── search_panel.py   # SearchPanel class
│   │   └── about_dialog.py   # AboutDialog class
│   │
│   ├── signature/            # E-signature functionality (coming soon)
│   │   ├── __init__.py
│   │   ├── canvas.py         # SignatureCanvas class
│   │   ├── metadata.py       # SignatureMetadataPanel class
│   │   ├── certificate.py    # CertificatePanel class
│   │   ├── position.py       # SignaturePositionPanel class
│   │   ├── dialog.py         # SignatureDialog class
│   │   └── service.py        # EndesiveService class
│   │
│   └── utils/                # Utility functions/classes
│       ├── __init__.py
│       ├── thumbnail.py      # ThumbnailViewDialog class
│       └── helpers.py        # Helper functions
│
└── resources/                # Images, icons, etc.
    ├── FreeBird.png
    └── pdf_icon.png
```

The organization alone should be enough to make the Adobe engineers quake in their ergonomic office chairs.

---

## Coming Soon: Digital Signatures - Because Scribbling on Your Screen Seemed Like a Good Idea

In our never-ending quest to eliminate all possible excuses for purchasing Adobe products, we're adding e-signature functionality through the power of Endesive integration:

- **Draw Your Signature:** Use your mouse like a pen, just way more awkward and imprecise!

- **Upload Signature Images:** For those who realized the mouse drawing looks like a 5-year-old's art project.

- **Certificate-Based Signatures:** For the serious businesspeople who need legal validity and won't settle for a JPG of a scribble.

- **Metadata Fields:** Add name, title, date, company, and other information that makes it look like you know what you're doing.

- **Position Anywhere:** Place your signature wherever you want on the document, ensuring maximum visual confusion for all future readers.

- **Multiple Signatures:** Because one questionable digital scribble isn't enough!

---

## Installation Options

### Option 1: Windows Executable (For the Command-Line Averse)

Can't be bothered with Python environments? We've got you covered with a pre-built Windows executable:

1. Download the latest installer from the [Releases](https://github.com/bruised-ego-labs/FreeBirdPDF/releases) page
2. Double-click and enjoy your newfound PDF freedom

_Note: The executable is approximately 50MB because it contains all necessary dependencies. Yes, that's larger than a text editor should be. No, we're not going to apologize for it._

### Option 2: From Source (For the Purists)

Fear not the complex installers of yesteryear! Project FreeBird requires only the sacred artifacts of the Python ecosystem:

1.  **Python:** Version 3.7+ recommended. If you don't have Python in 2025, are you even trying?
2.  **Pip:** The package manager that definitely won't break your system (probably).
3.  **Virtual Environment (Recommended):** Isolate the sheer power of this application. Navigate to the project directory in your terminal and run:
    ```bash
    python -m venv .venv
    ```
4.  **Activate the Portal:** Engage the virtual environment.
    - Windows (PowerShell): `.\.venv\Scripts\Activate.ps1` (You might need to appease the `Set-ExecutionPolicy` gods first).
    - Windows (CMD): `.\.venv\Scripts\activate.bat`
    - macOS/Linux: `source .venv/bin/activate`
5.  **Install the Arcane Libraries:** With the venv active, chant the following:

    ```bash
    pip install PyQt6 PyMuPDF
    ```

    For upcoming e-signature functionality:

    ```bash
    pip install endesive cryptography asn1crypto pillow
    ```

6.  **Invoke the Spell:** Run the application with:
    ```bash
    python FreeBirdPDF.py
    ```

---

## How to Use Advanced Features

### Page Reordering

- **Context Menu:** Right-click on any page to access "Move Page Up", "Move Page Down", or "Move Page To..." options
- **Reorder Button:** Click the "Reorder Pages" button to enter our revolutionary drag-and-drop thumbnail view
- **Keyboard Shortcuts:** Press Ctrl+Shift+Up or Ctrl+Shift+Down to move the current page

### Document Search

- **Search Bar:** Press Ctrl+F or click the "Search" button to reveal our state-of-the-art text search panel
- **Search Options:** Configure case sensitivity and whole word matching to your heart's content
- **Result Navigation:** Easily move between search hits with "Next" and "Previous" buttons or F3/Shift+F3

### Document Assembly

- **Multi-tab Magic:** Open several PDFs, then right-click on pages and add them to the assembly
- **Perfect Order:** Use our reordering tools to arrange your assembly document exactly as needed
- **Save:** Press Ctrl+S to save your masterpiece when it's ready

### E-Signatures (Coming Soon)

- **Sign Document:** Click the "Sign" button to add your digital signature
- **Multiple Signature Types:** Draw, upload, or use certificate-based signatures
- **Metadata:** Add name, title, company, date, and other information to your signature
- **Position Control:** Place signatures anywhere on the document
- **Compliance:** Signatures will adhere to appropriate digital signature standards

---

## How to Contribute

Did you stumble upon this project and, against all odds, find yourself wanting to contribute? We're less surprised now that our codebase isn't a horrifying monolith! Here's how:

1. **Fork the Repository:** Click that Fork button. You know you want to.
2. **Clone Your Fork:** `git clone https://github.com/yourusername/FreeBirdPDF.git`
3. **Create a Branch:** `git checkout -b fix-that-obvious-bug`
4. **Make Changes:** Preferably improvements, but we'll take what we can get.
5. **Push Changes:** `git push origin fix-that-obvious-bug`
6. **Submit a Pull Request:** Then wait patiently while Patch the Eagle struggles to remember how GitHub works.

### Development Guidelines

- **Code Style:** Python that runs is good Python. Python in the correct directory is even better Python.
- **Comments:** If your code is particularly mystifying, consider leaving breadcrumbs for future archaeologists.
- **Tests:** We've heard good things about them.
- **Version Tracking:** We follow a sophisticated versioning scheme called "numbers that get bigger."
- **Module Organization:** Put things where they belong. UI stuff in ui/, signature stuff in signature/, etc.

## Support the Project

If this humble project has saved you from subscription fees or just brought a smile to your face, consider supporting Bruised Ego Labs:

- **GitHub Sponsors:** Coming soon! (Patch needs to eat)
- **Star the Repo:** It costs nothing and feeds our fragile egos.
- **Share the Project:** Tell your friends, especially the ones who complain about Adobe.
- **Contribute Code:** See above.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Bruised Ego Labs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Acknowledgements

FreeBirdPDF was created with the assistance of several AI tools, each contributing their unique talents:

- **Gemini Advanced 2.5 Pro:** The initial mastermind who kickstarted this project and quickly adapted to our witty sarcasm.
- **ChatGPT 4.0:** Their image generator deftly birthed Patch the Eagle in all his majestic glory.
- **Claude 3.7 Sonnet (with extended thinking):** The wise elder of LLMs who swooped in to clean everything up as the code grew longer and then performed a complete architectural refactoring when things got out of hand.

Additional thanks to:

- **PyMuPDF** for making PDF manipulation possible without selling our souls.
- **PyQt6** for bringing the 90s desktop UI aesthetic into the modern era.
- **Endesive** for providing e-signature capabilities that don't require a PhD in cryptography.
- **You** for reading this far. Seriously, did you really read all of this?

## Contact

Have questions? Found a bug that wasn't intentional? Want to tell us how much better commercial PDF software is?

Email Patch the Eagle: patch.the.eagle@gmail.com

---

_Created with an equal mix of code, humor, mild frustration at proprietary PDF tools, and the dulcet sounds of Patch the Eagle screeching "FREEDOM!" in the background while admiring our new clean folder structure._
