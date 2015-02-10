gulp = require "gulp"
markdownPdf = require "gulp-markdown-pdf"
ignore = require "gulp-ignore"
shell = require "gulp-shell"
clean = require "gulp-clean"


gulp.task "pdf-clean", ->
  gulp.src("./pdf")
  .pipe(clean())
  
gulp.task "make-images", ->


  gulp.src ["./**/*.chart", "!./node_modules/**"]
  .pipe(shell(["./node_modules/.bin/mermaid --png <%= file.path %>"]))
  

gulp.task "make-pdf", ["pdf-clean", "make-images"], ->

  
  gulp.src ["./**/*.md", '!./node_modules/**']
  .pipe(ignore.exclude("./node_modules/**/*.md"))
  .pipe(markdownPdf({
      cssPath: "node_modules/bootstrap/dist/bootstrap.css"
      
    }))
  .pipe(gulp.dest("./pdf/"))
  
gulp.task "pdf", ['make-pdf'], ->

  # clean images
  gulp.src ["./**/*.chart.png", "!./node_modules/**"]
  .pipe(clean())