import AppKit
import ImageIO
import UniformTypeIdentifiers
import Vision
import JarvisCore

/// CGImage is immutable, so handing it to a background task is safe; this just says so to the compiler.
struct SendableImage: @unchecked Sendable { let image: CGImage }

/// Screenshots for the model and Apple Vision OCR with positions. Everything stays on this Mac.
enum ComputerImaging {
    /// A JPEG exactly `width` x `height` pixels (not points), as base64, so the coordinates the model sees are the pixels of this picture.
    nonisolated static func jpegBase64(_ image: CGImage, width: Int, height: Int, quality: Double = 0.65) -> String? {
        guard width > 0, height > 0,
              let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                                  bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return nil }
        ctx.interpolationQuality = .medium
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        guard let scaled = ctx.makeImage() else { return nil }
        let data = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(data, UTType.jpeg.identifier as CFString, 1, nil) else { return nil }
        CGImageDestinationAddImage(dest, scaled, [kCGImageDestinationLossyCompressionQuality: quality] as CFDictionary)
        guard CGImageDestinationFinalize(dest) else { return nil }
        return (data as Data).base64EncodedString()
    }

    struct TextBox { var text: String; var rect: CGRect }            // rect in IMAGE pixels, origin top-left

    /// Same recogniser settings as PageReader (accurate, language correction), but keeps where each line is. Used when the Accessibility tree is thin.
    nonisolated static func recognizeBoxes(_ image: CGImage) -> [TextBox] {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        do { try VNImageRequestHandler(cgImage: image, options: [:]).perform([request]) } catch { return [] }
        let w = CGFloat(image.width), h = CGFloat(image.height)
        return (request.results ?? []).compactMap { obs in
            guard let c = obs.topCandidates(1).first, c.confidence > 0.4, !c.string.trimmingCharacters(in: .whitespaces).isEmpty else { return nil }
            let b = obs.boundingBox                                     // normalised, origin bottom-left
            return TextBox(text: c.string, rect: CGRect(x: b.minX * w, y: (1 - b.maxY) * h, width: b.width * w, height: b.height * h))
        }.sorted { ($0.rect.minY, $0.rect.minX) < ($1.rect.minY, $1.rect.minX) }
    }
}
