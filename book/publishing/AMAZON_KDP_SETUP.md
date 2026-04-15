# Amazon KDP (Kindle Direct Publishing) Setup Guide

## Overview

Amazon KDP is the fastest path to getting *Thinking in Cognitive Architecture* available for purchase worldwide. KDP handles both Kindle eBook and Print-on-Demand paperback/hardcover.

**KDP Dashboard:** https://kdp.amazon.com

---

## Step 1: Create Your KDP Account

1. Go to https://kdp.amazon.com
2. Sign in with an existing Amazon account or create a new one
3. Complete your **Tax Information** (W-9 for US residents, W-8BEN for international)
4. Set up your **Bank Account** for royalty payments
5. Choose your **Marketplace** (recommend: Amazon.com, Amazon.co.uk, Amazon.de at minimum)

---

## Step 2: Prepare Your Manuscript Files

### For Kindle eBook:
- **Format:** Upload the DOCX file (`Thinking_in_Cognitive_Architecture.docx`)
- KDP's Kindle Create tool will auto-convert to Kindle format
- **Alternative:** Convert to EPUB using pandoc for more control:
  ```
  pandoc COMPLETE.md --to epub3 --toc -o book.epub
  ```

### For Print (Paperback / Hardcover):
- **Interior:** Upload the PDF (`Thinking_in_Cognitive_Architecture.pdf`)
- **Recommended trim size:** 6" x 9" (standard non-fiction)
- **Paper type:** White paper (cream for literary fiction)
- **Bleed:** No bleed (text-only interior)
- **Margins:** KDP requires minimum margins based on page count:
  - Inside margin: 0.375" (for books under 150 pages) to 0.875" (for 400+ pages)
  - Outside/Top/Bottom: 0.25" minimum
- **Page count estimate:** ~350-400 pages at 6x9, 11pt font

### Cover:
- **Kindle:** Front cover only, 2560 x 1600 pixels (recommended)
- **Print:** Full wrap cover (front + spine + back), template from KDP Cover Calculator
- **Cover Calculator:** https://kdp.amazon.com/cover-calculator
- **Recommendation:** Hire a professional cover designer ($200-500) — cover sells the book

---

## Step 3: Create Your Kindle eBook

1. Click **"Create New Title"** → **"Kindle eBook"**
2. **Book Details:**
   - Title: *Thinking in Cognitive Architecture*
   - Subtitle: *A Formal Language for the Human and Artificial Mind*
   - Author: Little Henderson
   - Description: (see below)
   - Keywords (7 max): `cognitive architecture`, `AI alignment`, `AI safety`, `cognitive science`, `category theory`, `artificial intelligence psychology`, `formal methods`
   - Categories: Select 2 BISAC categories
     - Computers > Artificial Intelligence > General
     - Psychology > Cognitive Psychology & Cognition
3. **Content:**
   - Upload DOCX or EPUB
   - Enable **DRM** (recommended to protect content)
4. **Pricing:**
   - Enroll in **KDP Select** (optional — gives 70% royalty but requires Amazon exclusivity for 90 days)
   - **Without KDP Select:** 35% royalty on prices below $2.99, 70% royalty on $2.99-$9.99
   - **Recommended eBook price:** $9.99 (maximizes the 70% royalty tier)

---

## Step 4: Create Your Print Edition

1. Click **"Create New Title"** → **"Paperback"** (or **"Hardcover"**)
2. **Print Details:**
   - Same metadata as eBook
   - ISBN: Enter your purchased ISBN, or use free KDP ISBN
   - Trim size: 6" x 9"
   - Paper: White
   - Ink: Black & White
3. **Upload Interior PDF**
4. **Upload Cover** (use KDP Cover Creator or upload custom PDF)
5. **Pricing:**
   - KDP calculates a **minimum list price** based on page count + printing cost
   - For a ~380-page 6x9 paperback, minimum is ~$8.50
   - **Recommended paperback price:** $29.99-$34.99 (standard for technical non-fiction)
   - **Recommended hardcover price:** $44.99-$49.99
   - Royalty: 60% of list price minus printing cost

---

## Step 5: Book Description (Amazon Listing)

```
What if the same structural laws that govern how a human translates 
intention into action also govern how an AI translates a prompt into 
a response?

THINKING IN COGNITIVE ARCHITECTURE introduces the Cognitive Architecture 
System (CAS)—a formal mathematical framework that maps the invisible 
geometry of thought across any substrate, biological or digital.

Whether you are a software engineer building AI systems, a leader 
diagnosing why your team is stalling, or an individual trying to 
understand why your habits never stick, this book provides the 
diagnostic vocabulary that psychology and computer science have 
been missing.

Inside you will find:
• 10 Cognitive Operators — the irreducible verbs of thought
• 4 Processing Domains — the vertical axis from ethics to execution
• 7 Core Drives — the motivational fuel system
• 40 Cognitive States — the periodic table of the mind
• 27 chapters of worked examples spanning career, relationships, 
  health, AI alignment, and formal mathematics
• The Noetic Compass assessment framework for measuring AI safety
• Exercises for both humans and AI systems in every chapter

From the boardroom to the neural network, from the therapist's 
couch to the Category Theory seminar, this book provides a single, 
unified language for the architecture of mind.
```

---

## Step 6: Launch Strategy

| Action | Timeline |
|--------|----------|
| Upload manuscript + cover | 4-6 weeks before launch |
| Order proof copy and review | 3-4 weeks before launch |
| Set up pre-order (optional) | 2-4 weeks before launch |
| Launch eBook + paperback | Launch day |
| Launch hardcover | Launch day or 1 week after |
| Request reviews from beta readers | Week 1 |
| Run KDP promotional pricing | Weeks 2-4 |

---

## Step 7: Expanded Distribution

- **KDP Print** automatically distributes to Amazon worldwide
- For bookstores and libraries, enable **Expanded Distribution** in KDP (reduces royalty but adds wholesale availability)
- For non-Amazon channels, consider:
  - **IngramSpark** (https://www.ingramspark.com) — broadest bookstore/library distribution
  - **Draft2Digital** (https://www.draft2digital.com) — aggregates to Apple Books, Kobo, Barnes & Noble
  - Both require your own ISBN

---

## Author Central

After publishing, set up your **Amazon Author Central** page:
- https://author.amazon.com
- Add author bio, photo, and blog
- Link all editions together
- Track sales rank and reviews
