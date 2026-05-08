# Matterflow AI Web Application

A modern Angular web application for legal matter creation, document upload, and AI-powered field extraction.

## Features

- Dynamic form fields loaded from templates
- File upload and document preview
- AI extraction of document fields with confidence badges
- Grouped and collapsible sections for AI and non-AI extracted fields
- Loader overlay during AI operations
- Professional, responsive UI

## Project Structure

- `src/app/` - Angular components and services
  - `template-fields/` - Dynamic form and AI extraction UI
  - `file-upload/` - File upload and preview
  - `document-details/` - Document preview and details
  - `services/` - Shared Angular services
- `public/templateData/` - JSON templates for field definitions
- `server.js` - (Optional) Node.js backend for API proxying

## Getting Started

### Prerequisites

- Node.js (v16+ recommended)
- Angular CLI (`npm install -g @angular/cli`)

### Installation

1. Clone the repository:
   ```sh
   git clone <your-repo-url>
   cd matterflow-ai-webapplication
   ```
2. Install dependencies:
   ```sh
   npm install
   ```

### Running the App

Start the Angular development server:

```sh
ng serve
```

Visit [http://localhost:4200](http://localhost:4200) in your browser.

### Backend API

- The app expects an AI extraction API at `http://127.0.0.1:8000/extract-matter-fields`.
- You can update the API endpoint in `src/app/template-fields/template-fields.ts` if needed.

## Customization

- Add or edit field templates in `public/templateData/`.
- Adjust UI styles in `src/app/template-fields/template-fields.css`.

## Deployment

- Build for production:
  ```sh
  ng build --prod
  ```
- Deploy the contents of the `dist/` folder to your web server.

## License

MIT

---

# Angular CLI Quick Reference

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 20.2.0.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
