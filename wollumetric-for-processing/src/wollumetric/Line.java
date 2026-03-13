package wollumetric;
import processing.core.*;

public class Line {
	private static int sliceWidth;
	public float x;
	public float z;
	private float screenXPos;
	private float projectedHeight;
	private Wollumetric wollumetric;

	/* Per-line calibration. calibWidth <= 0 means "use default sliceWidth". */
	private int calibWidth = -1;
	private int calibOffset = 0;

	public Line(float lineX, float lineZ, float screenXPos, float projectedHeight, Wollumetric wollumetric) {
		this.x = lineX;
		this.z = lineZ;
		this.screenXPos = screenXPos;
		this.projectedHeight = projectedHeight;
		this.wollumetric = wollumetric;
	}

	/**
	 * Set per-line calibration width and offset.
	 *
	 * @param width   pixel width for this line (1 .. sliceWidth)
	 * @param offset  pixel offset within the slot (0 .. sliceWidth - width)
	 */
	public void setCalibration(int width, int offset) {
		this.calibWidth = width;
		this.calibOffset = offset;
	}

	private int getEffectiveWidth() {
		return calibWidth > 0 ? calibWidth : sliceWidth;
	}

	private float getEffectiveScreenX() {
		return screenXPos + calibOffset;
	}

	/**
	* Draws on the line.  The two points can be anywhere from 0 to wollumetric.max.y
	* Numbers outside these bounds get clamped to be within the bounds
	*
	* @param  y1	Value 1
	* @param  y2	Value 2
	*/
	private float getYMin() {
		return wollumetric.vShiftAnchor * (wollumetric.size.y - projectedHeight);
	}

	private float getYMax() {
		return getYMin() + projectedHeight;
	}

	public void draw(float y1, float y2) {
		float yMin = getYMin();
		float yMax = getYMax();

		float top = y1 > y2 ? y1 : y2;
		float bot = top == y1 ? y2 : y1;
		float clampTop = Math.max(yMin, Math.min(yMax, top));
		float clampBot = Math.max(yMin, Math.min(yMax, bot));
		float drawHeight = clampTop - clampBot;

		float rectTop = PApplet.map(clampTop,
			yMax, yMin,
			0, Wollumetric.pApplet.height);
		float rectHeight = PApplet.map(drawHeight,
			0, projectedHeight,
			0, Wollumetric.pApplet.height);

		PMatrix3D invMatrix;
		invMatrix = wollumetric.getGfx().modelviewInv.get();
		invMatrix.apply(wollumetric.getGfx().camera);

		Wollumetric.pApplet.pushMatrix();
		Wollumetric.pApplet.pushStyle();
			Wollumetric.pApplet.applyMatrix(invMatrix);
			Wollumetric.pApplet.noStroke();
			Wollumetric.pApplet.rect(getEffectiveScreenX(), rectTop, getEffectiveWidth(), rectHeight);
		Wollumetric.pApplet.popStyle();
		Wollumetric.pApplet.popMatrix();
	}

	public static void setSliceWidth(int inSliceWidth) {
		Line.sliceWidth = inSliceWidth;
	}

	public void renderMap(PGraphics mapBuffer) {
		float effectiveX = getEffectiveScreenX();
		int effectiveWidth = getEffectiveWidth();
		float sizeY = wollumetric.size.y;
		float yMin = getYMin();
		float yMax = getYMax();

		int xColor = (int) PApplet.map(	this.x,
										0, wollumetric.size.x,
										0, 255);
		int zColor = (int) PApplet.map(	this.z,
										0, wollumetric.size.z,
										0, 255);
		for (int i = 0; i < Wollumetric.pApplet.height; i++) {
			float yForI = PApplet.map(	i,
										0, Wollumetric.pApplet.height,
										yMax, yMin);
			float yColor = PApplet.map(	yForI,
										0, sizeY,
										0, 255 * 255);
			int yColor1 = (int) Math.floor(yColor / 255.0f);
			int yColor2 = (int) (yColor - yColor1 * 255.0f);
			mapBuffer.stroke(xColor, yColor1, zColor, yColor2);
			mapBuffer.line(effectiveX, i, effectiveX + effectiveWidth, i);
	    }
	}
}