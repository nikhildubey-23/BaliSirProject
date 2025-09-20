# Bootstrap Optimization Task

## Analysis of Current CSS

### Areas to Replace with Bootstrap Classes:

#### 1. **Grid Systems & Layout**
- Custom flexbox layouts → Bootstrap grid system (`col-`, `row`, `container`)
- Custom spacing → Bootstrap spacing utilities (`m-`, `p-`, `mt-`, `mb-`)
- Custom alignment → Bootstrap alignment utilities (`justify-content-`, `align-items-`)

#### 2. **Typography**
- Custom font weights → Bootstrap typography (`fw-bold`, `fw-normal`)
- Custom font sizes → Bootstrap typography (`fs-1` to `fs-6`)
- Custom text alignment → Bootstrap text utilities (`text-center`, `text-start`)

#### 3. **Colors & Backgrounds**
- Custom colors → Bootstrap color utilities (`text-primary`, `bg-warning`)
- Custom background gradients → Bootstrap background utilities

#### 4. **Components**
- Custom buttons → Bootstrap button classes (`btn`, `btn-primary`)
- Custom forms → Bootstrap form classes (`form-control`, `form-label`)
- Custom cards → Bootstrap card component
- Custom alerts → Bootstrap alert component

#### 5. **Responsive Design**
- Custom media queries → Bootstrap responsive utilities
- Custom breakpoints → Bootstrap breakpoint classes

#### 6. **Interactive Elements**
- Custom hover effects → Bootstrap interaction utilities
- Custom focus states → Bootstrap focus utilities

## Implementation Plan

### Phase 1: Update HTML Templates
1. **Base Template** - Update with Bootstrap grid and utilities
2. **Index Page** - Replace custom layouts with Bootstrap grid
3. **About Page** - Convert sections to Bootstrap components
4. **Service Pages** - Update with Bootstrap cards and grids

### Phase 2: Remove Redundant CSS
1. Remove custom grid CSS
2. Remove custom spacing CSS
3. Remove custom color CSS
4. Remove custom component CSS
5. Keep only essential custom styles (animations, unique designs)

### Phase 3: Testing
1. Test all pages for layout integrity
2. Verify responsive behavior
3. Check accessibility features

## Expected Benefits

1. **Reduced CSS file size** by 60-80%
2. **Better maintainability** using standard Bootstrap classes
3. **Improved consistency** across the application
4. **Better accessibility** with Bootstrap's built-in ARIA support
5. **Faster development** using pre-built components

## Files to Update

### HTML Templates:
- templates/base.html
- templates/index.html
- templates/about.html
- templates/marine_cargo_insurance.html
- templates/fire_burglary_insurance.html
- templates/shopkeeper_insurance.html
- templates/workmen_compensation.html

### CSS File:
- public/css/style.css (significant reduction expected)

## Custom Styles to Keep

1. **Animations** (typing effects, custom transitions)
2. **Unique visual elements** (yellow circle, custom shapes)
3. **Brand-specific styling** (company colors, logos)
4. **Complex layouts** that Bootstrap can't handle efficiently
